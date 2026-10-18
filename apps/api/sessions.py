"""Supabase Auth password/rotating refresh tokens, held encrypted server-side."""
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from apps.api.accounts import AccountStore, digest

COOKIE='__Host-cockpit'
router=APIRouter(prefix='/api/v1/auth')


def same_origin(request):
    expected=request.app.state.settings.public_app_url.rstrip('/')
    received=request.headers.get('origin','')
    if received != expected:
        # Origin contains no path/query. Return only a validated scheme+host to
        # help diagnose a stale PWA/proxy origin without logging request data.
        try:
            parsed=urlsplit(received)
            shown=(parsed.scheme+'://'+parsed.netloc if parsed.scheme in ('http','https')
                   and parsed.hostname and not parsed.username and not parsed.password
                   and parsed.path in ('','/') and not parsed.query and not parsed.fragment else 'ausente ou inválida')
        except ValueError:
            shown='ausente ou inválida'
        raise HTTPException(403,f'Origem não autorizada. A API espera {expected}; o navegador enviou {shown}.')


class Login(BaseModel):
    email: str = Field(min_length=3,max_length=254)
    password: str = Field(min_length=1,max_length=1024)


class SessionStore(AccountStore):
    def provider(self, method, path, **kwargs):
        try:
            with httpx.Client(timeout=10,follow_redirects=False) as client:
                response=client.request(method,self.settings.supabase_url+'/auth/v1/'+path,
                    headers={'apikey':self.settings.supabase_key,**kwargs.pop('headers',{})},**kwargs)
            if response.status_code in (400,401,403):
                raise HTTPException(401,'Acesso inválido ou sessão expirada')
            if response.status_code not in (200,204):
                raise HTTPException(503,'Autenticação indisponível')
            return response.json() if response.content else {}
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            raise HTTPException(503,'Autenticação indisponível') from None

    def verified(self, access):
        user=self.provider('GET','user',headers={'Authorization':'Bearer '+access})
        try: UUID(user['id'])
        except (KeyError,ValueError,TypeError): raise HTTPException(401,'Sessão inválida') from None
        if user.get('is_anonymous'):raise HTTPException(403,'Acesso administrativo necessário')
        return {'id':user['id'],'email':user.get('email')}

    def create(self,email,password):
        data=self.provider('POST','token?grant_type=password',json={'email':email,'password':password})
        return self.create_verified(data)

    def create_verified(self,data):
        try:
            access,refresh,seconds=data['access_token'],data['refresh_token'],int(data['expires_in'])
            if not access or not refresh or seconds<=0:raise ValueError()
        except (KeyError,TypeError,ValueError):raise HTTPException(503,'Resposta Auth inválida') from None
        user=self.verified(access)
        if not any(m['role'] in ('admin','operator') for m in self.memberships(user['id'])):raise HTTPException(403,'Usuário sem acesso ao cockpit')
        sid,csrf=secrets.token_urlsafe(48),secrets.token_urlsafe(32)
        now=datetime.now(timezone.utc)
        with self.connect() as c:
            c.execute('INSERT INTO instagram_link.cockpit_sessions(session_hash,user_id,encrypted_session,access_expires_at,csrf_token,expires_at) VALUES (%s,%s,%s,%s,%s,%s)',(digest(sid),user['id'],self.cipher.encrypt(json.dumps({'access_token':access,'refresh_token':refresh}).encode()),now+timedelta(seconds=seconds),csrf,now+timedelta(seconds=self.settings.cockpit_session_seconds)))
        return sid,{'user':user,'csrf_token':csrf}

    def accept_invitation(self,access,refresh):
        # Both tokens must identify the same existing, authorized user.
        # Membership checked before rotation: an unbound invite does not consume its refresh token.
        user=self.verified(access)
        if not any(m['role'] in ('admin','operator') for m in self.memberships(user['id'])):
            raise HTTPException(403,'Seu acesso ainda não foi vinculado. Aguarde o administrador.')
        data=self.provider('POST','token?grant_type=refresh_token',json={'refresh_token':refresh})
        renewed=self.verified(data.get('access_token',''))
        if renewed['id']!=user['id']:
            raise HTTPException(401,'Convite inválido')
        return self.create_verified(data)

    def update_password(self,sid,password):
        self.resolve(sid)
        with self.connect() as c:
            row=c.execute('SELECT user_id,encrypted_session FROM instagram_link.cockpit_sessions WHERE session_hash=%s AND expires_at>now() FOR UPDATE',(digest(sid),)).fetchone()
            if not row:raise HTTPException(401,'Sessão expirada')
            data=json.loads(self.cipher.decrypt(bytes(row['encrypted_session'])))
            user=self.provider('PUT','user',headers={'Authorization':'Bearer '+data['access_token']},json={'password':password})
            if str(user.get('id'))!=str(row['user_id']):raise HTTPException(503,'Não foi possível confirmar a atualização da senha')
            return {'password_updated':True}

    def resolve(self,sid):
        if not sid or len(sid)>256:raise HTTPException(401,'Sessão ausente ou expirada')
        # Row lock serializes refresh rotation across tabs/processes; no reused refresh tokens.
        with self.connect() as c:
            row=c.execute('SELECT * FROM instagram_link.cockpit_sessions WHERE session_hash=%s AND expires_at>now() FOR UPDATE',(digest(sid),)).fetchone()
            if not row:raise HTTPException(401,'Sessão ausente ou expirada')
            data=json.loads(self.cipher.decrypt(bytes(row['encrypted_session'])))
            refresh=row['access_expires_at']<=datetime.now(timezone.utc)+timedelta(seconds=30)
            if not refresh:
                try:user=self.verified(data['access_token'])
                except HTTPException as error:
                    if error.status_code!=401:raise
                    refresh=True  # Server clock/provider expiry may differ; try the stored refresh once.
            if refresh:
                renewed=self.provider('POST','token?grant_type=refresh_token',json={'refresh_token':data['refresh_token']})
                try:
                    data={'access_token':renewed['access_token'],'refresh_token':renewed['refresh_token']}
                    seconds=int(renewed['expires_in'])
                    if not all(data.values()) or seconds<=0:raise ValueError()
                except (KeyError,ValueError,TypeError):raise HTTPException(503,'Resposta Auth inválida') from None
                # Commit token rotation before a second network verification. A transient GET failure
                # must not roll back the newly issued refresh token and lose the user's session.
                if str(renewed.get('user',{}).get('id',row['user_id']))!=str(row['user_id']):
                    raise HTTPException(401,'Identidade de sessão divergente')
                c.execute('UPDATE instagram_link.cockpit_sessions SET encrypted_session=%s,access_expires_at=%s WHERE session_hash=%s',(self.cipher.encrypt(json.dumps(data).encode()),datetime.now(timezone.utc)+timedelta(seconds=seconds),digest(sid)))
                c.commit()
                user=self.verified(data['access_token'])
            if user['id']!=str(row['user_id']):raise HTTPException(401,'Sessão inválida')
            return {'user':user,'csrf_token':row['csrf_token']}

    def remove(self,sid):
        with self.connect() as c:
            row=c.execute('DELETE FROM instagram_link.cockpit_sessions WHERE session_hash=%s RETURNING encrypted_session',(digest(sid),)).fetchone()
        if row:
            data=json.loads(self.cipher.decrypt(bytes(row['encrypted_session'])))
            try:self.provider('POST','logout?scope=local',headers={'Authorization':'Bearer '+data['access_token']})
            except HTTPException:pass  # Local cookie/session invalidated even if provider is unavailable.


async def cookie_session(request):
    cached=getattr(request.state,'cockpit_session',None)
    if cached:return cached
    result=await run_in_threadpool(request.app.state.sessions.resolve,request.cookies.get(COOKIE,''))
    request.state.cockpit_session=result
    return result


async def csrf(request):
    same_origin(request)
    session=await cookie_session(request)
    if not hmac.compare_digest(request.headers.get('X-CSRF-Token',''),session['csrf_token']):
        raise HTTPException(403,'Verificação de sessão inválida')
    return session


@router.post('/login')
async def login(request:Request,body:Login,response:Response):
    same_origin(request)
    sid,result=await run_in_threadpool(request.app.state.sessions.create,body.email,body.password)
    response.set_cookie(COOKIE,sid,max_age=request.app.state.settings.cockpit_session_seconds,secure=True,httponly=True,samesite='lax',path='/')
    response.headers['Cache-Control']='private, no-store'
    return result


@router.get('/session')
async def session(request:Request):
    return await cookie_session(request)


@router.post('/logout')
async def logout(request:Request,response:Response):
    await csrf(request)
    await run_in_threadpool(request.app.state.sessions.remove,request.cookies.get(COOKIE,''))
    response.delete_cookie(COOKIE,secure=True,httponly=True,samesite='lax',path='/')
    response.delete_cookie('instagram_oauth_browser',secure=True,httponly=True,samesite='lax',path='/api/v1/instagram')
    return {'signed_out':True}


class InviteSession(BaseModel):
    access_token:str=Field(min_length=1,max_length=8192)
    refresh_token:str=Field(min_length=1,max_length=8192)


class PasswordChange(BaseModel):
    password:str=Field(min_length=12,max_length=1024)
    confirmation:str=Field(min_length=12,max_length=1024)


@router.post('/invitation/session')
async def invitation_session(request:Request,body:InviteSession,response:Response):
    same_origin(request)
    sid,result=await run_in_threadpool(request.app.state.sessions.accept_invitation,body.access_token,body.refresh_token)
    response.set_cookie(COOKIE,sid,max_age=request.app.state.settings.cockpit_session_seconds,secure=True,httponly=True,samesite='lax',path='/')
    response.headers['Cache-Control']='private, no-store'
    return result


@router.post('/password')
async def password(request:Request,body:PasswordChange):
    await csrf(request)
    if body.password!=body.confirmation:raise HTTPException(422,'As senhas devem ser iguais')
    return await run_in_threadpool(request.app.state.sessions.update_password,request.cookies.get(COOKIE,''),body.password)
