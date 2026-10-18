import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from apps.api.auth import current_user
from packages.meta.oauth import authorization_url, exchange_code, subscribe_comments, MetaOAuthError

router = APIRouter(prefix='/api/v1')
COOKIE = 'instagram_oauth_browser'


@router.get('/auth/me')
async def me(request: Request, user=Depends(current_user)):
    memberships = await run_in_threadpool(request.app.state.accounts.memberships,user['id'])
    if not memberships:
        raise HTTPException(403, 'Usuário sem vínculo de acesso')
    return {'user': user, 'memberships': memberships}


@router.get('/instagram/accounts')
async def accounts(request: Request, organization_id: UUID, user=Depends(current_user)):
    try:
        items = await run_in_threadpool(request.app.state.accounts.list_accounts,user['id'],organization_id)
        return {'items': items}
    except PermissionError:
        raise HTTPException(403, 'Acesso negado') from None


@router.get('/instagram/connect')
async def connect(request: Request, organization_id: UUID, account_id: UUID = None, user=Depends(current_user)):
    """OAuth para admin/operator do vínculo; reconexão restrita à mesma conta e organização."""
    config = request.app.state.settings
    if not config.oauth_ready:
        raise HTTPException(503, 'Instagram Login não configurado; verificar credenciais Instagram e callback HTTPS')
    browser = secrets.token_urlsafe(48)
    try:
        state = await run_in_threadpool(request.app.state.accounts.create_state,user['id'],organization_id,browser,account_id)
    except PermissionError:
        raise HTTPException(403, 'Acesso negado') from None
    # Fetch with the verified cockpit session; then navigate to the official authorization URL.
    from fastapi.responses import JSONResponse
    response = JSONResponse({'authorization_url':authorization_url(config,state)})
    response.set_cookie(COOKIE,browser,max_age=600,httponly=True,secure=True,samesite='lax',path='/api/v1/instagram')
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.get('/instagram/callback')
async def callback(request: Request):
    config = request.app.state.settings
    if not config.oauth_ready:
        raise HTTPException(503, 'Instagram Login não configurado')
    state = request.query_params.get('state','')
    browser = request.cookies.get(COOKIE,'')
    if not state or not browser:
        raise HTTPException(400, 'State inválido ou expirado')
    try:
        context = await run_in_threadpool(request.app.state.accounts.consume_state,state,browser)
    except PermissionError:
        raise HTTPException(400, 'State inválido ou expirado') from None
    if request.query_params.get('error'):
        raise HTTPException(400, 'Autorização recusada')
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(400, 'Código ausente')
    try:
        profile,token,scopes,expires = await exchange_code(config,code)
        account_id = await run_in_threadpool(request.app.state.accounts.save_connection,context,profile,token,scopes,expires)
    except MetaOAuthError:
        raise HTTPException(502, 'Não foi possível validar a autorização Instagram') from None
    except PermissionError:
        raise HTTPException(409, 'Conta incompatível com o vínculo solicitado') from None
    try:
        subscription = await subscribe_comments(config,profile['user_id'],token)
    except MetaOAuthError:
        subscription = 'failed'
    await run_in_threadpool(request.app.state.accounts.subscription_result,account_id,subscription)
    response = RedirectResponse('/m0/connect?instagram=connected&comments=' + subscription,status_code=303)
    response.delete_cookie(COOKIE,path='/api/v1/instagram',secure=True,httponly=True,samesite='lax')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@router.get('/instagram/history')
async def history(request: Request, organization_id: UUID, account_id: UUID, user=Depends(current_user)):
    try:
        items = await run_in_threadpool(request.app.state.accounts.cockpit_history, user['id'], organization_id, account_id)
        return {'items': items, 'dispatches_paused': request.app.state.settings.dispatches_paused}
    except PermissionError:
        raise HTTPException(403, 'Acesso negado') from None


@router.post('/instagram/accounts/{account_id}/pause')
async def pause(request: Request, account_id: UUID, organization_id: UUID, user=Depends(current_user)):
    try:
        return await run_in_threadpool(request.app.state.accounts.pause_account, user['id'], organization_id, account_id)
    except PermissionError:
        raise HTTPException(403, 'Acesso negado') from None
