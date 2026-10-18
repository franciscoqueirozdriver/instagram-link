"""Verify bearer tokens with the project's Supabase Auth service, never decode-only."""
from uuid import UUID

import httpx
from fastapi import HTTPException, Request


async def current_user(request: Request):
    header = request.headers.get('authorization', '')
    if not header:
        from apps.api.sessions import cookie_session, csrf
        session = await cookie_session(request)
        if request.method not in ('GET','HEAD','OPTIONS'):
            await csrf(request)
        return session['user']
    if not header.startswith('Bearer ') or not header[7:].strip():
        raise HTTPException(401, 'Sessão ausente ou inválida')
    config = request.app.state.settings
    if not config.supabase_url or not config.supabase_key:
        raise HTTPException(503, 'Supabase Auth não configurado')
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.get(config.supabase_url + '/auth/v1/user', headers={
                'apikey': config.supabase_key, 'Authorization': header})
        if response.status_code in (401, 403):
            raise HTTPException(401, 'Sessão ausente ou inválida')
        if response.status_code != 200:
            raise HTTPException(503, 'Autenticação indisponível')
        user = response.json()
        UUID(user['id'])
        if user.get('is_anonymous'):
            raise HTTPException(403, 'Acesso administrativo necessário')
        return {'id': user['id'], 'email': user.get('email')}
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, 'Autenticação indisponível') from None
