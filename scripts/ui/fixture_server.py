"""Isolated browser fixture. No production credentials/database/provider calls."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from datetime import datetime,timezone,timedelta
from cryptography.fernet import Fernet
from fastapi import Request,HTTPException
from apps.api.config import Settings
from apps.api.main import create_app
from packages.meta.oauth import SCOPES

ORG='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
FIRST='11111111-1111-4111-8111-111111111111'
SECOND='22222222-2222-4222-8222-222222222222'
USER='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
OPERATOR='cccccccc-cccc-4ccc-8ccc-cccccccccccc'
class Inbox:
    def ready(self):pass
class Store:
    def __init__(self):
        self.states={}
        self.items=[dict(id=id,ig_user_id=ig,username=name,connection_status='connected',scopes=list(SCOPES),expires_at=(datetime.now(timezone.utc)+timedelta(days=50)).isoformat(),paused=paused,comments_subscription_status='accepted') for id,ig,name,paused in [(FIRST,'111','atelier.demo',True),(SECOND,'222','estudio.demo',False)]]
    def memberships(self,user):return [{'organization_id':ORG,'role':'operator' if str(user)==OPERATOR else 'admin'}]
    def list_accounts(self,user,org):
        if str(org)!=ORG:raise PermissionError()
        return [{k:v for k,v in row.items() if str(user)!=OPERATOR or k not in ('scopes','ig_user_id')} for row in self.items]
    def cockpit_history(self,user,org,account):
        if str(account)!=FIRST:return []
        return [dict(status=status,attempt_count=1,dispatched_at='2026-10-17T04:50:37Z',finished_at=None,http_status=200 if status=='accepted' else None) for status in ['accepted','failed','unknown']]
    def pause_account(self,user,org,account):
        if str(user)==OPERATOR:raise PermissionError()
        return {'paused':True}
    def create_state(self,user,org,browser,account_id=None):
        if str(org)!=ORG or (account_id and not any(row['id']==str(account_id) for row in self.items)):raise PermissionError()
        state=secrets.token_urlsafe(32)
        self.states[state]={'user_id':user,'organization_id':org,'account_id':account_id,'browser':browser}
        return state
    def consume_state(self,state,browser):
        row=self.states.get(state)
        if not row or row['browser']!=browser:raise PermissionError()
        return self.states.pop(state)
    def save_connection(self,context,profile,token,scopes,expires):
        if str(context['organization_id'])!=ORG:raise PermissionError()
        row=next((row for row in self.items if row['ig_user_id']==profile['user_id']),None)
        if context['account_id'] and (not row or row['id']!=str(context['account_id'])):raise PermissionError()
        if not row:
            row={'id':str(uuid4()),'ig_user_id':profile['user_id']};self.items.append(row)
        row.update(username=profile['username'],connection_status='connected',scopes=scopes,paused=True,expires_at=(datetime.now(timezone.utc)+timedelta(seconds=expires)).isoformat(),comments_subscription_status='pending')
        return row['id']
    def subscription_result(self,account,status):next(row for row in self.items if row['id']==account)['comments_subscription_status']=status
    def credential_snapshot(self,id):return {'id':id,'token':'synthetic-instagram-token','ig_user_id':'111'}
    def apply_token_health(self,*args):return False
config=Settings('postgresql://unused','synthetic-secret','synthetic-verify',Fernet.generate_key().decode(),'synthetic-infra',supabase_url='http://127.0.0.1:8011',supabase_key='sb_publishable_fixture',instagram_app_id='12345',instagram_app_secret='synthetic-ig-secret',redirect_uri='https://example.invalid/api/v1/instagram/callback')
# New cookie/session + catalog fixtures are confined to this test-only app.
import secrets
from uuid import uuid4,UUID
from contextlib import contextmanager
from types import SimpleNamespace
from dataclasses import replace
from packages.domain.campaigns import render_message
import apps.api.catalog_routes as catalog_routes

class Sessions:
    def __init__(self):self.sessions={}
    def create(self,email,password):
        if password!='fixture-only':raise HTTPException(401,'Invalid synthetic credentials')
        sid=secrets.token_urlsafe(32);data={'user':{'id':OPERATOR if email=='operator@example.invalid' else USER},'csrf_token':'synthetic-csrf'};self.sessions[sid]=data
        return sid,data
    def resolve(self,sid):
        if sid not in self.sessions:raise HTTPException(401,'Expired')
        return self.sessions[sid]
    def accept_invitation(self,access,refresh):
        if (access,refresh)!=('synthetic-invite','synthetic-refresh'):raise HTTPException(401,'Invalid synthetic invite')
        return self.create('operator@example.invalid','fixture-only')
    def update_password(self,sid,password):
        self.resolve(sid)
        return {'password_updated':True}
    def remove(self,sid):self.sessions.pop(sid,None)

class Catalog:
    def __init__(self):self.p=[];self.m=[];self.c=[];self.r=[];self.logs=[];self.details={};self.sync={}
    @contextmanager
    def connect(self):yield None
    def account(self,c,user,org,account):return {'connection_status':'connected','expires_at':datetime.now(timezone.utc)+timedelta(days=30),'scopes':list(SCOPES)}
    def products(self,user,org):return self.p
    def save_product(self,user,org,data,pid=None):
        old=next((p for p in self.p if str(p['id'])==str(pid)),None)
        row={**data,'id':str(pid or uuid4()),'version':old['version']+1 if old else 1}
        self.p=[p for p in self.p if p['id']!=row['id']]+[row];return row
    def archive_product(self,user,org,pid,version):
        row=next(p for p in self.p if p['id']==str(pid));row['active']=False;return row
    def publications(self,user,org,account):return [r for r in self.m if r['account_id']==str(account)]
    def save_publications(self,user,org,account,items,*,sync_state=None,next_after=None):
        for i,item in enumerate(items):
            pid=str(UUID(int=UUID('33333333-3333-4333-8333-333333333333').int+int(item['id'])-123456))
            row={**item,'id':pid,'ig_media_id':item['id'],'account_id':str(account),'published_at':item['timestamp']}
            self.m=[r for r in self.m if r['id']!=pid or r['account_id']!=str(account)]+[row]
        self.sync[str(account)]={'after':next_after,'synced_at':datetime.now(timezone.utc)}
    def sync_state(self,user,org,account):return self.sync.get(str(account),{'after':None,'synced_at':None})
    def publications_page(self,user,org,account,cursor=None,limit=12):
        rows=self.publications(user,org,account);offset=int(cursor or 0);items=rows[offset:offset+limit];end=str(offset+len(items))
        state=self.sync_state(user,org,account)
        return {'items':items,'end_cursor':end,'next_cursor':end if offset+len(items)<len(rows) else None,'has_more_remote':bool(state['after']),'synced_at':state['synced_at']}
    def campaigns(self,user,org,account):return [r for r in self.c if r['account_id']==str(account)]
    def campaign(self,user,org,account,cid):return next(r for r in self.c if r['id']==str(cid))
    def save_campaign(self,user,org,account,data,cid=None):
        product=next(p for p in self.p if p['id']==str(data['product_id']))
        old=next((c for c in self.c if c['id']==str(cid)),None)
        row={**data,'id':str(cid or uuid4()),'account_id':str(account),'publication_id':str(data['publication_id']),'product_id':str(data['product_id']),'product_snapshot':product.copy(),'version':old['version']+1 if old else 1,'state':'draft','created_at':old['created_at'] if old else datetime.now(timezone.utc),'permalink':'https://www.instagram.com/p/synthetic/','caption':'Publicação de demonstração','published_at':datetime.now(timezone.utc),'media_type':'IMAGE','media_url':'/fixture/thumb.svg','rules':{k:data[k] for k in ['include','exclude','ignore_accents']},'rendered_message':render_message(data['template'],product,config)}
        self.c=[c for c in self.c if c['id']!=row['id']]+[row];self.logs.append({'action':'campaign_version_saved','version':row['version'],'created_at':datetime.now(timezone.utc),'name':row['name']});return row
    def archive_campaign(self,user,org,account,cid,version):
        row=self.campaign(user,org,account,cid);row['state']='archived';return {'archived':True}
    def pause_campaign(self,user,org,account,cid,version):
        self.campaign(user,org,account,cid)['state']='paused'
        self.logs.append({'action':'campaign_paused','version':version,'created_at':datetime.now(timezone.utc),'name':self.campaign(user,org,account,cid)['name']})
        return {'paused':True}
    def versions(self,user,org,account,cid):
        row=self.campaign(user,org,account,cid)
        return [{k:row[k] for k in ['version','rules','product_snapshot','template','rendered_message','created_at']}]
    def review_detail(self,user,org,account,rid):return self.details[str(rid)]
    def prior_attempts(self,account):return set()
    def save_review(self,user,org,account,cid,version,review):
        c=self.campaign(user,org,account,cid);c['state']='paused';row={'id':str(uuid4()),'campaign_id':str(cid),'campaign_version':version,'created_at':datetime.now(timezone.utc),'expires_at':datetime.now(timezone.utc)+timedelta(minutes=15),'name':c['name']};self.r.append(row);self.details[row['id']]={**review,**row,'version':version,'expired':False,'stale':False};return row
    def reviews(self,user,org,account):return self.r
    def audit_history(self,user,org,account):return self.logs

config=replace(config,public_app_url='http://127.0.0.1:8011',meta_api_version='v26.0',meta_max_message_length=1000,meta_message_length_unit='bytes')
fixture_store=Store()
def fixture_media_page(settings,snapshot,after=None):
    offset=int(after or 0);base=123456 if str(snapshot['id'])==FIRST else 223456
    items=[{'id':str(base+i),'caption':('Publicação de demonstração' if i==0 else 'Reel de demonstração '+str(i)) if base==123456 else 'Publicação de outra conta '+str(i),'permalink':'https://www.instagram.com/'+('reel' if i%3==1 else 'p')+'/synthetic'+str(i)+'/','media_type':'VIDEO' if i%3==1 else 'IMAGE','media_product_type':'REELS' if i%3==1 else 'FEED','media_url':'/fixture/thumb.svg','thumbnail_url':'/fixture/thumb.svg' if i%3==1 else None,'timestamp':datetime.now(timezone.utc)-timedelta(days=i)} for i in range(offset,min(offset+25,40))]
    return items,str(offset+25) if offset+25<40 else None
catalog_routes.media_page=fixture_media_page
catalog_routes.media=lambda settings,snapshot:([{'id':'123456'}],False)
catalog_routes.comments=lambda settings,snapshot,mid:([
 {'id':'100','from':{'id':'88','username':'pessoa.demo'},'text':'Quero o LINK!','hidden':False,'timestamp':datetime.now(timezone.utc).isoformat()},
 {'id':'101','from':{'id':'89','username':'outra.demo'},'text':'CANCELAR LINK','hidden':False,'timestamp':datetime.now(timezone.utc).isoformat()}],False)
import apps.api.oauth_routes as oauth_routes
async def fixture_exchange(settings,code):
    if code not in ('synthetic-new','synthetic-reconnect'):raise oauth_routes.MetaOAuthError('synthetic-denied')
    return ({'user_id':'333' if code=='synthetic-new' else '111','username':'nova.demo' if code=='synthetic-new' else 'atelier.demo'},'synthetic-private-token',list(SCOPES),5184000)
async def fixture_subscription(*args):return 'accepted'
oauth_routes.exchange_code=fixture_exchange
oauth_routes.subscribe_comments=fixture_subscription
app=create_app(config,Inbox(),fixture_store,sessions=Sessions(),catalog=Catalog())

@app.post('/fixture/reset')
async def reset_fixture():
    app.state.accounts=Store()
    app.state.catalog=Catalog()
    app.state.sessions=Sessions()
    return {'synthetic_reset':True}

@app.post('/fixture/empty-accounts')
async def empty_accounts():
    app.state.accounts.items=[]
    return {'synthetic_empty':True}

@app.get('/fixture/thumb.svg')
async def fixture_thumb():
    from fastapi.responses import Response
    return Response('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect width="400" height="400" fill="#e4ece3"/><rect x="130" y="105" width="140" height="190" rx="18" fill="#335e4b"/><circle cx="200" cy="155" r="28" fill="#dbe4c0"/><text x="200" y="340" text-anchor="middle" font-size="20" fill="#192c26">Demonstração</text></svg>',media_type='image/svg+xml')
