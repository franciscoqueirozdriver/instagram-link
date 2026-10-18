import hmac
import logging
import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apps.api.accounts import AccountStore
from apps.api.oauth_routes import router
from apps.api.connect_page import router as connect_page_router
from apps.api.privacy import router as privacy_router
from apps.api.pwa import router as pwa_router
from apps.api.sessions import SessionStore, router as sessions_router
from apps.api.catalog import CatalogStore
from apps.api.catalog_routes import router as catalog_router
from apps.api.shopee_config import ShopeeCredentialStore
from apps.api.shopee_routes import router as shopee_router
from apps.api.webhook_diagnostics import WebhookDiagnostics
from apps.api.config import configured
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from starlette.concurrency import run_in_threadpool

from apps.api.config import Settings, ENV_FILE
from apps.api.inbox import PostgresInbox
from packages.meta.webhook import valid_signature


def create_app(settings=None, inbox=None, accounts=None, sessions=None, catalog=None, shopee_config=None):
    @asynccontextmanager
    async def lifespan(app):
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        app.state.settings = settings or Settings.from_env()
        app.state.inbox = inbox or PostgresInbox(
            app.state.settings.database_url, app.state.settings.encryption_key)
        app.state.accounts = accounts or AccountStore(app.state.settings)
        app.state.sessions = sessions or SessionStore(app.state.settings)
        app.state.catalog = catalog or CatalogStore(app.state.settings)
        app.state.shopee_config = shopee_config or ShopeeCredentialStore(app.state.settings)
        app.state.webhook_diagnostics = WebhookDiagnostics()
        yield

    app = FastAPI(title='Instagram Link — M0', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)

    load_dotenv(ENV_FILE, override=False, interpolate=False)
    origin = settings.public_app_url if settings else os.environ.get('PUBLIC_APP_URL', '')
    app.add_middleware(CORSMiddleware, allow_origins=[origin] if origin else [],
                       allow_credentials=True, allow_methods=['GET'],
                       allow_headers=['Authorization', 'Content-Type'])
    app.include_router(router)
    app.include_router(connect_page_router)
    app.include_router(privacy_router)
    app.include_router(pwa_router)
    app.include_router(sessions_router)
    app.include_router(catalog_router)
    app.include_router(shopee_router)

    @app.middleware('http')
    async def sanitized_failures(request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            return error(503, 'dependency_unavailable', 'Dependência indisponível')
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(422, 'invalid_input', 'Confira os campos informados')

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(exc.status_code, 'http_' + str(exc.status_code), str(exc.detail))

    def error(status, code, message):
        return JSONResponse(status_code=status, content={'error': {
            'code': code, 'message': message, 'request_id': str(uuid4()), 'details': {}}})

    @app.get('/health/live')
    async def live():
        return {'status': 'ok'}

    @app.get('/health/ready')
    async def ready(request: Request):
        supplied = request.headers.get('X-Infra-Key', '')
        if not hmac.compare_digest(supplied.encode(), request.app.state.settings.infra_key.encode()):
            return error(403, 'forbidden', 'Acesso negado')
        try:
            await run_in_threadpool(request.app.state.inbox.ready)
        except Exception:
            return error(503, 'storage_unavailable', 'Persistência indisponível')
        return {'status': 'ok'}

    @app.get('/health/webhook')
    async def webhook_diagnostics(request: Request):
        supplied = request.headers.get('X-Infra-Key', '')
        if not hmac.compare_digest(supplied.encode(), request.app.state.settings.infra_key.encode()):
            return error(403, 'forbidden', 'Acesso negado')
        return request.app.state.webhook_diagnostics.snapshot()

    @app.get('/webhooks/instagram')
    async def verify(request: Request):
        query = request.query_params
        token = query.get('hub.verify_token', '')
        expected = request.app.state.settings.verify_token
        if query.get('hub.mode') != 'subscribe':
            outcome = 'invalid_mode'
        elif not query.get('hub.challenge'):
            outcome = 'missing_challenge'
        elif not hmac.compare_digest(token.encode(), expected.encode()):
            outcome = 'token_mismatch'
        else:
            outcome = 'accepted'
        request.app.state.webhook_diagnostics.verification(outcome)
        if outcome != 'accepted':
            return error(403, 'invalid_verification', 'Verificação inválida')
        return PlainTextResponse(query['hub.challenge'])

    @app.post('/webhooks/instagram')
    async def receive(request: Request):
        config = request.app.state.settings
        diagnostics = request.app.state.webhook_diagnostics
        diagnostics.observe()
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > config.max_body_bytes:
                diagnostics.decide('payload_too_large')
                return error(413, 'payload_too_large', 'Payload excedeu limite')
            body.extend(chunk)
        raw = bytes(body)
        if not configured(config.app_secret):
            diagnostics.decide('missing_secret')
            return error(503, 'meta_not_configured', 'Assinatura Meta ainda não configurada')
        if not valid_signature(raw, request.headers.get('X-Hub-Signature-256', ''), config.app_secret):
            diagnostics.decide('invalid_signature')
            # Diagnostic-only comparison. The rejected request remains 403 and is
            # never persisted, even if it matches another locally held secret.
            if (configured(config.instagram_app_secret)
                    and config.instagram_app_secret != config.app_secret
                    and valid_signature(raw, request.headers.get('X-Hub-Signature-256', ''), config.instagram_app_secret)):
                diagnostics.note_oauth_match_on_rejection()
            return error(403, 'invalid_signature', 'Assinatura inválida')
        # Guardar inclusive formato desconhecido; não inferir contrato Meta sem M0.
        try:
            await run_in_threadpool(request.app.state.inbox.save, raw)
        except Exception:
            diagnostics.decide('storage_unavailable')
            return error(503, 'storage_unavailable', 'Persistência indisponível')
        diagnostics.decide('persisted')
        return {'status': 'persisted'}

    return app


app = create_app()
