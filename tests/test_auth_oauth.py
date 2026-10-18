from dataclasses import replace
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import httpx
import pytest

from apps.api.auth import current_user
from apps.api.config import Settings
from apps.api.main import create_app
from packages.meta.oauth import authorization_url, exchange_code, SCOPES, MetaOAuthError
from tests.test_webhook import Inbox


@pytest.fixture
def config():
    return Settings('postgresql://localhost/test', 'test-secret', 'test-verify',
                    Fernet.generate_key().decode(),'infra-test',
                    supabase_url='https://project.supabase.co',supabase_key='public-test',
                    instagram_app_id='12345',instagram_app_secret='ig-secret',
                    meta_api_version='v25.0',redirect_uri='https://api.test/api/v1/instagram/callback')


class Accounts:
    def __init__(self):
        self.states = {}
        self.saved = []
        self.subscriptions = []

    def memberships(self,user_id):
        return [{'organization_id':str(uuid4()),'role':'admin'}]

    def create_state(self,user_id,org_id,browser,account_id=None):
        self.states['test-state'] = browser
        return 'test-state'

    def consume_state(self,state,browser):
        if self.states.get(state) != browser:
            raise PermissionError()
        del self.states[state]
        return {'user_id':str(uuid4()),'organization_id':str(uuid4()),'account_id':None}

    def save_connection(self,*args):
        self.saved.append(args)
        return 'test-account'

    def subscription_result(self,account_id,status):
        self.subscriptions.append((account_id,status))


def test_auth_requires_verified_user(config,monkeypatch):
    app = create_app(config,Inbox(),Accounts())
    user_id = str(uuid4())
    called = []
    async def get(self,url,headers):
        called.append(url)
        if headers['Authorization'] == 'Bearer valid-token':
            return httpx.Response(200,json={'id':user_id,'email':'test@example.invalid'})
        return httpx.Response(401,json={'message':'provider-sensitive-details'})
    monkeypatch.setattr(httpx.AsyncClient,'get',get)
    with TestClient(app) as client:
        assert client.get('/api/v1/auth/me').status_code == 401
        denied = client.get('/api/v1/auth/me',headers={'Authorization':'Bearer forged'})
        assert denied.status_code == 401
        assert 'provider-sensitive' not in denied.text
        result = client.get('/api/v1/auth/me',headers={'Authorization':'Bearer valid-token'})
        assert result.status_code == 200
        assert result.json()['user']['id'] == user_id
    assert called == [config.supabase_url+'/auth/v1/user'] * 2


def test_authorization_contract(config):
    url = urlsplit(authorization_url(config,'random-state'))
    assert url.hostname == 'www.instagram.com'
    query = parse_qs(url.query)
    assert query['client_id'] == ['12345']
    assert set(query['scope'][0].split(',')) == set(SCOPES)
    assert 'client_secret' not in query
    assert 'facebook.com' not in url.netloc


def test_oauth_cookie_binding_and_replay(config,monkeypatch):
    accounts = Accounts()
    app = create_app(config,Inbox(),accounts)
    app.dependency_overrides[current_user] = lambda: {'id':str(uuid4())}
    async def fake_exchange(settings,code):
        return {'user_id':'123456','username':'test'},'private-token',list(SCOPES),3600
    monkeypatch.setattr('apps.api.oauth_routes.exchange_code',fake_exchange)
    async def fake_subscribe(*args):
        return 'confirmed'
    monkeypatch.setattr('apps.api.oauth_routes.subscribe_comments',fake_subscribe)
    with TestClient(app,base_url='https://api.test') as client:
        connected = client.get('/api/v1/instagram/connect',params={'organization_id':str(uuid4())})
        assert connected.status_code == 200
        assert 'HttpOnly' in connected.headers['set-cookie']
        assert 'Secure' in connected.headers['set-cookie']
        callback = '/api/v1/instagram/callback?state=test-state&code=private-code'
        with TestClient(app,base_url='https://api.test') as other:
            assert other.get(callback).status_code == 400
        result = client.get(callback,follow_redirects=False)
        assert result.status_code == 303
        assert 'private-token' not in result.text + result.headers.get('location','')
        assert len(accounts.saved) == 1
        assert accounts.subscriptions == [('test-account','confirmed')]
        assert result.headers['location'].startswith('/m0/connect?')
        assert client.get(callback).status_code == 400


def test_missing_oauth_config_stays_closed(config):
    app = create_app(replace(config,instagram_app_secret=''),Inbox(),Accounts())
    app.dependency_overrides[current_user] = lambda: {'id':str(uuid4())}
    with TestClient(app) as client:
        assert client.get('/api/v1/instagram/connect',params={'organization_id':str(uuid4())}).status_code == 503


def test_refuse_unpaused(config):
    with pytest.raises(ValueError):
        replace(config,dispatches_paused=False)


@pytest.mark.parametrize('version', ['v25.0', 'v26.0'])
def test_exchange_no_facebook_and_missing_permissions(config,monkeypatch,version):
    config = replace(config, meta_api_version=version)
    requests = []
    async def post(self,url,data):
        requests.append(url)
        assert data['client_id'] == config.instagram_app_id
        return httpx.Response(200,json={'access_token':'short','permissions':list(SCOPES)})
    async def get(self,url,**kwargs):
        requests.append(url)
        if url.endswith('/access_token'):
            return httpx.Response(200,json={'access_token':'long','expires_in':3600})
        return httpx.Response(200,json={'user_id':'123456','username':'test'})
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    monkeypatch.setattr(httpx.AsyncClient,'get',get)
    import asyncio
    result = asyncio.run(exchange_code(config,'code'))
    assert result[1] == 'long'
    assert all('facebook.com' not in url for url in requests)
    assert requests[-1] == 'https://graph.instagram.com/' + version + '/me'
    async def denied_post(self,url,data):
        return httpx.Response(200,json={'access_token':'short','permissions':[]})
    monkeypatch.setattr(httpx.AsyncClient,'post',denied_post)
    with pytest.raises(MetaOAuthError):
        asyncio.run(exchange_code(config,'code'))


def test_cors_restricted_to_cockpit(config):
    app = create_app(config,Inbox(),Accounts())
    with TestClient(app) as client:
        result = client.options('/api/v1/auth/me',headers={
            'Origin':config.public_app_url,'Access-Control-Request-Method':'GET',
            'Access-Control-Request-Headers':'authorization'})
        assert result.status_code == 200
        assert result.headers['access-control-allow-origin'] == config.public_app_url
        denied = client.options('/api/v1/auth/me',headers={
            'Origin':'https://attacker.invalid','Access-Control-Request-Method':'GET'})
        assert denied.status_code == 400


def test_connect_page_has_only_public_configuration(config):
    public = replace(config,supabase_key='sb_publishable_test')
    with TestClient(create_app(public,Inbox(),Accounts())) as client:
        result = client.get('/m0/connect')
        assert result.status_code == 200
        assert 'sb_publishable_test' in result.text
        assert all(secret not in result.text for secret in [config.encryption_key,config.infra_key,config.instagram_app_secret,config.database_url])
        assert "frame-ancestors 'none'" in result.headers['content-security-policy']
        assert 'localStorage' not in result.text
    with TestClient(create_app(replace(config,supabase_key='sb_secret_forbidden'),Inbox(),Accounts())) as client:
        assert client.get('/m0/connect').status_code == 503


def test_comments_subscription_never_sends_messages(config,monkeypatch):
    import asyncio
    from packages.meta.oauth import subscribe_comments
    calls=[]
    async def post(self,url,headers,data):
        calls.append(url)
        assert data == {'subscribed_fields':'comments'}
        assert headers['Authorization']=='Bearer private-token'
        return httpx.Response(200,json={'success':True})
    async def get(self,url,headers):
        calls.append(url)
        return httpx.Response(200,json={'data':[{'id':config.instagram_app_id,'subscribed_fields':['comments']}]})
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    monkeypatch.setattr(httpx.AsyncClient,'get',get)
    assert asyncio.run(subscribe_comments(config,'123456','private-token'))=='confirmed'
    assert all(url.endswith('/123456/subscribed_apps') for url in calls)
    assert not any('/messages' in url for url in calls)
    async def rejected(self,url,headers,data):
        return httpx.Response(400,json={'error':{'message':'sensitive'}})
    monkeypatch.setattr(httpx.AsyncClient,'post',rejected)
    with pytest.raises(MetaOAuthError):
        asyncio.run(subscribe_comments(config,'123456','private-token'))
