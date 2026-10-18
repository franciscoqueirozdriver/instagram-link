"""Public installation assets only. Never caches API/session data."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

router = APIRouter()
ASSETS = Path(__file__).with_name('assets')


@router.get('/manifest.webmanifest')
async def manifest():
    return JSONResponse({'id':'/m0/connect','name':'MyAgentSales — Cockpit','short_name':'MyAgentSales','lang':'pt-BR','start_url':'/m0/connect','scope':'/','display':'standalone','background_color':'#f5f6f2','theme_color':'#163d32','icons':[{'src':'/assets/icon-192.png','sizes':'192x192','type':'image/png','purpose':'any'},{'src':'/assets/icon-512.png','sizes':'512x512','type':'image/png','purpose':'any maskable'}]}, media_type='application/manifest+json')


@router.get('/assets/{name}')
async def asset(name: str):
    if name not in ('icon-192.png','icon-512.png'):
        raise HTTPException(404, 'Arquivo não encontrado')
    return FileResponse(ASSETS / name, media_type='image/png')


@router.get('/offline', response_class=HTMLResponse)
async def offline():
    return HTMLResponse('''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline · MyAgentSales</title></head><body><main><h1>Você está offline</h1><p>Conecte-se à internet para acessar suas contas. Dados privados e ações de envio não estão disponíveis offline.</p><a href="/m0/connect">Tentar novamente</a></main></body></html>''', headers={'Content-Security-Policy':"default-src 'none'; base-uri 'none'; frame-ancestors 'none'",'X-Content-Type-Options':'nosniff'})


@router.get('/service-worker.js')
async def service_worker():
    return Response(ASSETS.joinpath('service-worker.js').read_text(), media_type='application/javascript', headers={'Service-Worker-Allowed':'/','Cache-Control':'no-store'})
