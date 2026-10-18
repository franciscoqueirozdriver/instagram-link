from uuid import UUID, uuid4
from dataclasses import replace
from fastapi.testclient import TestClient
from apps.api.auth import current_user
from apps.api.main import create_app
from tests.test_auth_oauth import config, Accounts
from tests.test_webhook import Inbox


class CockpitAccounts(Accounts):
    def cockpit_history(self, user, org, account):
        if account != UUID('11111111-1111-4111-8111-111111111111'):
            raise PermissionError()
        return [{'status':'unknown','attempt_count':1,'http_status':None}]

    def pause_account(self, user, org, account):
        if account != UUID('11111111-1111-4111-8111-111111111111'):
            raise PermissionError()
        return {'paused':True}


def test_cockpit_routes_require_auth_and_scope(config):
    app=create_app(config,Inbox(),CockpitAccounts())
    account='11111111-1111-4111-8111-111111111111'
    params={'organization_id':str(uuid4()),'account_id':account}
    with TestClient(app) as client:
        assert client.get('/api/v1/instagram/history',params=params).status_code==401
        assert client.post('/api/v1/instagram/accounts/'+account+'/pause',params=params).status_code==401
        app.dependency_overrides[current_user]=lambda:{'id':str(uuid4())}
        assert client.get('/api/v1/instagram/history',params=params).json()['items'][0]['status']=='unknown'
        assert client.post('/api/v1/instagram/accounts/'+account+'/pause',params=params).json()=={'paused':True}
        params['account_id']=str(uuid4())
        assert client.get('/api/v1/instagram/history',params=params).status_code==403
        assert client.post('/api/v1/instagram/accounts/'+params['account_id']+'/pause',params=params).status_code==403
        assert client.post('/api/v1/instagram/accounts/'+account+'/resume',params=params).status_code==404


def test_installation_assets_are_public_and_scope_limited(config):
    with TestClient(create_app(replace(config,supabase_key='sb_publishable_test'),Inbox(),Accounts())) as client:
        assert client.get('/manifest.webmanifest').json()['display']=='standalone'
        assert client.get('/assets/icon-192.png').headers['content-type']=='image/png'
        assert client.get('/assets/cockpit.js').status_code==404
        sw=client.get('/service-worker.js')
        assert sw.headers['service-worker-allowed']=='/'
        assert client.get('/offline').status_code==200
        assert 'PUBLIC.includes(url.pathname)' in sw.text


def test_pilot_requires_positive_and_negative_checks_before_provider_or_dispatch(config):
    class Catalog:
        def campaign(self,*args):return {'version':1,'rules':{'include':['LINK'],'exclude':['CANCELAR'],'ignore_accents':False}}
    app=create_app(config,Inbox(),CockpitAccounts(),catalog=Catalog())
    app.dependency_overrides[current_user]=lambda:{'id':str(uuid4())}
    cid=str(uuid4());params={'organization_id':str(uuid4()),'account_id':str(uuid4())}
    with TestClient(app) as client:
        result=client.post('/api/v1/catalog/campaigns/'+cid+'/prepare-pilot',params=params,json={'expected_version':1,'positive':'LINK','negative':'LINK'})
        assert result.status_code==422
        assert client.post('/api/v1/catalog/campaigns/'+cid+'/activate',params=params).status_code==404
