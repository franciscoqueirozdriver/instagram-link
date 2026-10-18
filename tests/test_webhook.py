import hashlib
import hmac

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.config import Settings
from apps.api.main import create_app


class Inbox:
    def __init__(self):
        self.bodies = set()
        self.fail = False

    def save(self, body):
        if self.fail:
            raise RuntimeError('secret database detail')
        self.bodies.add(body)

    def ready(self):
        if self.fail:
            raise RuntimeError('secret database detail')


@pytest.fixture
def setup():
    settings = Settings('postgresql://localhost/test', 'test-secret',
                        'verify-secret', Fernet.generate_key().decode(), 'infra-secret')
    inbox = Inbox()
    with TestClient(create_app(settings, inbox)) as client:
        yield client, inbox


def signed(body):
    return {'X-Hub-Signature-256': 'sha256=' + hmac.new(
        b'test-secret', body, hashlib.sha256).hexdigest()}


def test_handshake(setup):
    client, _ = setup
    params = {'hub.mode': 'subscribe', 'hub.verify_token': 'verify-secret', 'hub.challenge': '123'}
    assert client.get('/webhooks/instagram', params=params).text == '123'
    params['hub.verify_token'] = 'wrong'
    assert client.get('/webhooks/instagram', params=params).status_code == 403


def test_signature_raw_bytes_and_replay(setup):
    client, inbox = setup
    body = b'{ "entry": [] }'
    assert client.post('/webhooks/instagram', content=body).status_code == 403
    assert client.post('/webhooks/instagram', content=body + b' ', headers=signed(body)).status_code == 403
    for _ in range(2):
        assert client.post('/webhooks/instagram', content=body, headers=signed(body)).status_code == 200
    assert inbox.bodies == {body}


def test_database_failure_does_not_ack_or_leak(setup):
    client, inbox = setup
    inbox.fail = True
    response = client.post('/webhooks/instagram', content=b'{}', headers=signed(b'{}'))
    assert response.status_code == 503
    assert 'secret database' not in response.text
    inbox.fail = False
    assert client.post('/webhooks/instagram', content=b'{}', headers=signed(b'{}')).status_code == 200


def test_limit_and_health(setup):
    client, inbox = setup
    assert client.post('/webhooks/instagram', content=b'x' * (1024 * 1024 + 1)).status_code == 413
    assert not inbox.bodies
    assert client.get('/health/live').status_code == 200
    assert client.get('/health/ready').status_code == 403
    assert client.get('/health/ready', headers={'X-Infra-Key': 'infra-secret'}).status_code == 200


def test_reject_placeholder():
    with pytest.raises(ValueError):
        Settings('', '', '', '', '')


def test_protected_diagnostics_separates_arrival_rejection_and_persistence(setup):
    client, inbox = setup
    assert client.get('/health/webhook').status_code == 403
    headers = {'X-Infra-Key':'infra-secret'}
    initial = client.get('/health/webhook',headers=headers).json()
    assert initial['received'] == 0
    body = b'{"sensitive_test":"do-not-return"}'
    assert client.post('/webhooks/instagram',content=body).status_code == 403
    assert client.post('/webhooks/instagram',content=body,headers=signed(body)).status_code == 200
    inbox.fail = True
    assert client.post('/webhooks/instagram',content=b'{}',headers=signed(b'{}')).status_code == 503
    response = client.get('/health/webhook',headers=headers)
    data=response.json()
    assert data['received'] == 3
    assert data['invalid_signature'] == 1
    assert data['persisted'] == 1
    assert data['storage_unavailable'] == 1
    assert data['last_outcome'] == 'storage_unavailable'
    assert 'do-not-return' not in response.text
    assert 'infra-secret' not in response.text


def test_alternate_secret_diagnostic_never_authorizes_or_persists(setup):
    from dataclasses import replace
    client, inbox = setup
    client.app.state.settings = replace(client.app.state.settings,instagram_app_secret='alternate-test-secret')
    body=b'{"test":"rejected-keep-private"}'
    signature='sha256='+hmac.new(b'alternate-test-secret',body,hashlib.sha256).hexdigest()
    response=client.post('/webhooks/instagram',content=body,headers={'X-Hub-Signature-256':signature})
    assert response.status_code==403
    assert not inbox.bodies
    diagnostics=client.get('/health/webhook',headers={'X-Infra-Key':'infra-secret'})
    assert diagnostics.json()['rejected_matches_instagram_oauth_secret']==1
    assert diagnostics.json()['persisted']==0
    assert 'alternate-test-secret' not in diagnostics.text
    assert 'rejected-keep-private' not in diagnostics.text
    assert client.get('/health/webhook').status_code==403


def test_verification_diagnostics_never_store_token_or_challenge(setup):
    client, inbox = setup
    path='/webhooks/instagram'
    params={'hub.mode':'subscribe','hub.verify_token':'verify-secret','hub.challenge':'private-challenge'}
    assert client.get(path,params=params).text=='private-challenge'
    params['hub.verify_token']='wrong-sensitive-value'
    assert client.get(path,params=params).status_code==403
    headers={'X-Infra-Key':'infra-secret'}
    response=client.get('/health/webhook',headers=headers)
    data=response.json()
    assert data['verification_received']==2
    assert data['verification_accepted']==1 and data['verification_rejected']==1
    assert data['verification_last_outcome']=='token_mismatch'
    assert all(value not in response.text for value in ('verify-secret','wrong-sensitive-value','private-challenge'))
    assert not inbox.bodies and data['received']==0
    assert client.get('/health/webhook').status_code==403
