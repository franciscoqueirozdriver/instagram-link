import asyncio
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

from cryptography.fernet import Fernet
import pytest
from fastapi import HTTPException

from apps.api.shopee_config import ShopeeCredentialStore
from apps.api.shopee_routes import ShopeeCredentials, credential_status, save_credentials
from apps.api.main import create_app
from apps.api.connect_page import connect_page
from tests.test_auth_oauth import config


class ShopeeConfigStub:
    def __init__(self):
        self.roles = {}
        self.saved = {}

    def status(self, user, organization):
        if self.roles.get((user, str(organization))) != 'admin':
            raise PermissionError()
        return {'configured': organization in self.saved, 'configured_at': None, 'updated_at': None}

    def save(self, user, organization, app_id, app_secret):
        if self.roles.get((user, str(organization))) != 'admin':
            raise PermissionError()
        self.saved[organization] = (app_id, app_secret)
        return {'configured': True}


def test_store_encrypts_credentials_and_checks_organization(config, monkeypatch):
    organization = uuid4()
    other_organization = uuid4()
    admin = str(uuid4())
    ciphertext = {}
    roles = {(admin, str(organization)): 'admin'}

    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, args):
            if query.startswith('SELECT role FROM instagram_link.memberships'):
                return Result({'role': roles.get((str(args[0]), str(args[1])))})
            if query.startswith('SELECT configured_at,updated_at'):
                exists = args[0] in ciphertext
                return Result({'configured_at': None, 'updated_at': None} if exists else None)
            if query.startswith('INSERT INTO instagram_link.shopee_organization_credentials'):
                ciphertext[args[0]] = bytes(args[1])
                return Result()
            if query.startswith('SELECT encrypted_credentials'):
                return Result({'encrypted_credentials': ciphertext.get(args[0])} if args[0] in ciphertext else None)
            raise AssertionError('Unexpected SQL in fake connection')

    store = ShopeeCredentialStore(config)
    monkeypatch.setattr(store, 'connect', Connection)
    assert store.status(admin, organization)['configured'] is False
    store.save(admin, organization, 'synthetic-app-id', 'synthetic-app-secret')
    encrypted = ciphertext[organization]
    assert b'synthetic-app-secret' not in encrypted
    assert Fernet(config.encryption_key.encode()).decrypt(encrypted).find(b'synthetic-app-secret') >= 0
    assert store.status(admin, organization)['configured'] is True
    assert store.credential_snapshot(admin, organization) == {
        'app_id': 'synthetic-app-id', 'app_secret': 'synthetic-app-secret'
    }
    with pytest.raises(PermissionError):
        store.status(admin, other_organization)
    with pytest.raises(PermissionError):
        store.credential_snapshot(admin, other_organization)


def test_credentials_routes_are_admin_only_and_never_return_secret(monkeypatch):
    organization = uuid4()
    other_organization = uuid4()
    admin = str(uuid4())
    operator = str(uuid4())
    store = ShopeeConfigStub()
    store.roles[(admin, str(organization))] = 'admin'
    store.roles[(operator, str(organization))] = 'operator'
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(shopee_config=store)))
    async def in_process(function, *args):
        return function(*args)
    monkeypatch.setattr('apps.api.shopee_routes.run_in_threadpool', in_process)
    params = {'app_id': 'synthetic-app-id', 'app_secret': 'synthetic-secret-value'}
    assert asyncio.run(credential_status(request, organization, {'id': admin}))['configured'] is False
    response = asyncio.run(save_credentials(request, organization, ShopeeCredentials(**params), {'id': admin}))
    assert response == {'configured': True}
    assert 'synthetic-secret-value' not in repr(response)
    assert asyncio.run(credential_status(request, organization, {'id': admin}))['configured'] is True
    with pytest.raises(HTTPException) as denied_other_org:
        asyncio.run(credential_status(request, other_organization, {'id': admin}))
    assert denied_other_org.value.status_code == 403
    with pytest.raises(HTTPException) as denied_operator:
        asyncio.run(credential_status(request, organization, {'id': operator}))
    assert denied_operator.value.status_code == 403
    with pytest.raises(HTTPException) as denied_write:
        asyncio.run(save_credentials(
            request, organization,
            ShopeeCredentials(app_id='other-id', app_secret='must-not-store'),
            {'id': operator},
        ))
    assert denied_write.value.status_code == 403
    assert all(secret != 'must-not-store' for _, secret in store.saved.values())


def test_openapi_marks_shopee_app_secret_write_only(config):
    schema = create_app(config).openapi()
    path = schema['paths']['/api/v1/shopee/credentials']['put']
    body_ref = path['requestBody']['content']['application/json']['schema']['$ref'].split('/')[-1]
    body = schema['components']['schemas'][body_ref]
    assert body['properties']['app_secret']['writeOnly'] is True
    response = path['responses']['200']['content']['application/json']['schema']
    assert 'app_secret' not in response.get('properties', {})


def test_cockpit_contains_admin_only_local_credentials_form(config):
    settings = replace(config, supabase_key='sb_publishable_test')
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))
    response = asyncio.run(connect_page(request))
    assert response.status_code == 200
    assert 'id="shopee-config" data-admin-only hidden' in response.body.decode()
    assert 'id="shopee-app-id"' in response.body.decode()
    assert 'id="shopee-app-secret"' in response.body.decode()
    assert 'name="app_secret"' in response.body.decode()
