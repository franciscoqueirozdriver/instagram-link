import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from dataclasses import replace
from apps.api.main import create_app
from apps.api.sessions import COOKIE
from tests.test_auth_oauth import config,Accounts
from tests.test_webhook import Inbox

class Sessions:
    def __init__(self):self.live=False
    def create(self,email,password):
        if password!='correct':raise HTTPException(401,'Invalid')
        self.live=True
        return 'opaque-test-session',{'user':{'id':'11111111-1111-4111-8111-111111111111'},'csrf_token':'csrf-only-test'}
    def resolve(self,sid):
        if not self.live or sid!='opaque-test-session':raise HTTPException(401,'Expired')
        return {'user':{'id':'11111111-1111-4111-8111-111111111111'},'csrf_token':'csrf-only-test'}
    def remove(self,sid):self.live=False


def test_cookie_restores_after_navigation_csrf_and_logout(config):
    config=replace(config,public_app_url='https://api.test')
    sessions=Sessions()
    with TestClient(create_app(config,Inbox(),Accounts(),sessions=sessions),base_url='https://api.test') as client:
        body={'email':'synthetic@example.invalid','password':'correct'}
        denied=client.post('/api/v1/auth/login',json=body)
        assert denied.status_code==403
        assert 'espera https://api.test' in denied.json()['error']['message']
        assert 'enviou ausente ou inválida' in denied.json()['error']['message']
        result=client.post('/api/v1/auth/login',json=body,headers={'Origin':'https://api.test'})
        assert result.status_code==200
        cookie=result.headers['set-cookie']
        assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Path=/' in cookie
        assert 'access_token' not in result.text and 'refresh_token' not in result.text
        assert client.get('/m0/connect?instagram=connected').status_code in (200,503)
        assert client.get('/api/v1/auth/session').status_code==200
        assert client.get('/api/v1/auth/me').status_code==200
        assert client.post('/api/v1/auth/logout',headers={'Origin':'https://api.test'}).status_code==403
        assert client.post('/api/v1/auth/logout',headers={'Origin':'https://attacker.invalid','X-CSRF-Token':'csrf-only-test'}).status_code==403
        assert client.post('/api/v1/auth/logout',headers={'Origin':'https://api.test','X-CSRF-Token':'csrf-only-test'}).status_code==200
        assert client.get('/api/v1/auth/session').status_code==401


def test_invalid_login_input_does_not_echo_password(config):
    with TestClient(create_app(config,Inbox(),Accounts(),sessions=Sessions())) as client:
        r=client.post('/api/v1/auth/login',json={'email':'a','password':'sensitive-input-not-to-echo'},headers={'Origin':config.public_app_url})
        assert r.status_code==422 and 'sensitive-input-not-to-echo' not in r.text


def test_invite_exchange_checks_same_user_and_membership_before_refresh(config,monkeypatch):
    from apps.api.sessions import SessionStore
    store=SessionStore(config)
    calls=[]
    monkeypatch.setattr(store,'verified',lambda token:{'id':'user-one' if token=='old-access' else 'user-two'})
    monkeypatch.setattr(store,'memberships',lambda uid:[{'role':'operator','organization_id':'one'}])
    monkeypatch.setattr(store,'provider',lambda *a,**kw: calls.append(a) or {'access_token':'new-access','refresh_token':'new-refresh','expires_in':3600})
    with pytest.raises(HTTPException):store.accept_invitation('old-access','refresh-for-other-user')
    assert len(calls)==1
    calls.clear()
    monkeypatch.setattr(store,'memberships',lambda uid:[])
    with pytest.raises(HTTPException):store.accept_invitation('old-access','old-refresh')
    assert not calls


def test_password_setup_requires_origin_csrf_and_matching_passwords(config):
    class InviteSessions(Sessions):
        def accept_invitation(self,access,refresh):return self.create('operator@example.invalid','correct')
        def update_password(self,sid,password):return {'password_updated':True}
    config=replace(config,public_app_url='https://api.test')
    store=InviteSessions()
    with TestClient(create_app(config,Inbox(),Accounts(),sessions=store),base_url='https://api.test') as client:
        body={'access_token':'synthetic-access','refresh_token':'synthetic-refresh'}
        assert client.post('/api/v1/auth/invitation/session',json=body).status_code==403
        r=client.post('/api/v1/auth/invitation/session',json=body,headers={'Origin':'https://api.test'})
        assert r.status_code==200 and 'synthetic-access' not in r.text and 'synthetic-refresh' not in r.text
        passwords={'password':'synthetic-strong-password','confirmation':'synthetic-strong-password'}
        assert client.post('/api/v1/auth/password',json=passwords,headers={'Origin':'https://api.test'}).status_code==403
        headers={'Origin':'https://api.test','X-CSRF-Token':'csrf-only-test'}
        assert client.post('/api/v1/auth/password',json=passwords,headers=headers).json()=={'password_updated':True}
        passwords['confirmation']='different-strong-password'
        assert client.post('/api/v1/auth/password',json=passwords,headers=headers).status_code==422
