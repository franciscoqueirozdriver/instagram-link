from dataclasses import replace

from fastapi.testclient import TestClient

from apps.api.main import create_app
from tests.test_auth_oauth import config, Accounts
from tests.test_webhook import Inbox


def test_privacy_public_and_no_secrets(config):
    with TestClient(create_app(config,Inbox(),Accounts())) as client:
        response=client.get('/privacy')
    assert response.status_code==200
    assert 'text/html' in response.headers['content-type']
    assert 'MyAgentSales' in response.text
    assert 'Aviso provisório' in response.text
    assert 'www-authenticate' not in response.headers
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    for secret in (config.database_url,config.encryption_key,config.infra_key,config.verify_token,config.instagram_app_secret,config.supabase_key):
        assert secret not in response.text


def test_explicit_contact_escaped_and_no_identity_inferred(config):
    settings=replace(config,privacy_controller_name='<script>evil()</script>',privacy_contact_email='privacy@example.invalid')
    with TestClient(create_app(settings,Inbox(),Accounts())) as client:
        response=client.get('/privacy')
    assert '<script>evil()' not in response.text
    assert '&lt;script&gt;evil()&lt;/script&gt;' in response.text
    assert 'mailto:privacy@example.invalid' in response.text
    assert 'Aviso provisório' not in response.text


def test_contact_url_cannot_inject_markup_or_use_javascript(config):
    settings=replace(config,privacy_controller_name='Responsável de teste',privacy_contact_url='javascript:alert(1)')
    with TestClient(create_app(settings,Inbox(),Accounts())) as client:
        response=client.get('/privacy')
    assert response.status_code==200
    assert 'javascript:' not in response.text
    assert 'Aviso provisório' in response.text
    assert 'canal ainda não informado' in response.text
