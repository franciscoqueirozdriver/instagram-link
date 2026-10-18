import json
import base64
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get('/m0/connect', response_class=HTMLResponse)
async def connect_page(request: Request):
    config = request.app.state.settings
    key = config.supabase_key
    safe_key = key.startswith('sb_publishable_')
    if not safe_key:
        try:
            segment = key.split('.')[1]
            safe_key = json.loads(base64.urlsafe_b64decode(segment + '=' * (-len(segment) % 4)))['role'] == 'anon'
        except (IndexError, KeyError, ValueError, TypeError):
            safe_key = False
    if not safe_key:
        raise HTTPException(503, 'Chave pública Supabase não configurada')
    nonce = secrets.token_urlsafe(24)
    public = json.dumps({'url':config.supabase_url,'key':config.supabase_key,'messageLimit':config.meta_max_message_length,'messageUnit':config.meta_message_length_unit}).replace('<','\\u003c')
    page = Path(__file__).with_name('pages').joinpath('connect.html').read_text()
    assets = Path(__file__).with_name('assets')
    page = page.replace('__CATALOG_HTML__', Path(__file__).with_name('pages').joinpath('catalog.html').read_text())
    page = page.replace('__CSS__', assets.joinpath('cockpit.css').read_text()).replace('__JS__', assets.joinpath('cockpit.js').read_text() + '\n' + assets.joinpath('catalog.js').read_text())
    page = page.replace('__NONCE__',nonce).replace('__CONFIG__',public)
    # Only the publishable key is public; no tokens or backend secrets in HTML.
    source = urlsplit(config.supabase_url)
    auth_origin = source.scheme + '://' + source.netloc
    response = HTMLResponse(page)
    response.headers['Content-Security-Policy'] = (
        "default-src 'none'; manifest-src 'self'; worker-src 'self'; img-src 'self' https://*.cdninstagram.com https://*.fbcdn.net; script-src 'nonce-"+nonce+"'; style-src 'nonce-"+nonce+
        "'; connect-src 'self' "+auth_origin+"; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response
