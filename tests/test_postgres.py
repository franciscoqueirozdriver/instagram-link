"""Banco isolado obrigatório: TEST_DATABASE_URL nunca deve apontar para produção."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest
from cryptography.fernet import Fernet

from apps.api.inbox import PostgresInbox


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='PostgreSQL isolado não configurado')
def test_migration_encryption_and_concurrent_replay(monkeypatch):
    url = os.environ['TEST_DATABASE_URL']
    with psycopg.connect(url) as connection:
        connection.execute(Path('db/migrations/001_m0_inbox.sql').read_text())
        connection.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon; END IF; IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated; END IF; END $$; CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY)")
        connection.execute(Path('db/migrations/002_supabase_accounts.sql').read_text())
        connection.execute(Path('db/migrations/003_comments_subscription.sql').read_text())
        connection.execute(Path('db/migrations/004_m0_single_reply.sql').read_text())
        connection.execute(Path('db/migrations/005_catalog_campaigns_sessions.sql').read_text())
        connection.execute(Path('db/migrations/006_visual_publications.sql').read_text())
        connection.execute(Path('db/migrations/007_shopee_organization_credentials.sql').read_text())
    key = Fernet.generate_key()
    inbox = PostgresInbox(url, key.decode())
    payload = b'{"entry":[],"test":"no-real-data"}'
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(inbox.save, [payload] * 100))
    inbox.ready()
    with psycopg.connect(url) as connection:
        rows = connection.execute('SELECT encrypted_payload FROM instagram_link.webhook_envelopes').fetchall()
    assert len(rows) == 1
    encrypted = bytes(rows[0][0])
    assert payload not in encrypted
    assert Fernet(key).decrypt(encrypted) == payload

    # Exercise the actual OAuth store with two accounts and organization isolation.
    from uuid import uuid4
    from psycopg.rows import dict_row
    from apps.api.accounts import AccountStore
    from apps.api.config import Settings
    from packages.meta.oauth import SCOPES
    user, org, other_org = uuid4(), uuid4(), uuid4()
    with psycopg.connect(url) as connection:
        connection.execute('INSERT INTO auth.users(id) VALUES (%s)',(user,))
        connection.execute('INSERT INTO instagram_link.organizations(id,name) VALUES (%s,%s),(%s,%s)',(org,'Test organization',other_org,'Other test organization'))
        connection.execute("INSERT INTO instagram_link.memberships(organization_id,user_id,role) VALUES (%s,%s,'admin')",(org,user))
    settings = Settings(url,'test-secret','test-verify',key.decode(),'test-infra',meta_max_message_length=1000,meta_message_length_unit='bytes')
    store = AccountStore(settings)
    monkeypatch.setattr(store,'connect',lambda: psycopg.connect(url,row_factory=dict_row))
    from apps.api.shopee_config import ShopeeCredentialStore
    shopee = ShopeeCredentialStore(settings)
    monkeypatch.setattr(shopee,'connect',lambda: psycopg.connect(url,row_factory=dict_row))
    assert shopee.status(user,org)['configured'] is False
    shopee.save(user,org,'synthetic-shopee-app-id','synthetic-shopee-app-secret')
    assert shopee.status(user,org)['configured'] is True
    with psycopg.connect(url) as connection:
        encrypted_shopee = bytes(connection.execute(
            'SELECT encrypted_credentials FROM instagram_link.shopee_organization_credentials WHERE organization_id=%s',(org,)
        ).fetchone()[0])
    assert b'synthetic-shopee-app-secret' not in encrypted_shopee
    assert shopee.credential_snapshot(user,org)=={
        'app_id':'synthetic-shopee-app-id','app_secret':'synthetic-shopee-app-secret'
    }
    with pytest.raises(PermissionError):
        shopee.credential_snapshot(user,other_org)
    with pytest.raises(PermissionError):
        shopee.save(user,other_org,'another-app-id','another-app-secret')
    state = store.create_state(user,org,'browser')
    with pytest.raises(PermissionError):
        store.consume_state(state,'wrong-browser')
    context = store.consume_state(state,'browser')
    with pytest.raises(PermissionError):
        store.consume_state(state,'browser')
    first = store.save_connection(context,{'user_id':'111','username':'one'},'token-one',list(SCOPES),3600)
    second = store.save_connection(context,{'user_id':'222','username':'two'},'token-two',list(SCOPES),3600)
    accounts = store.list_accounts(user,org)
    assert len(accounts)==2 and all(a['paused'] for a in accounts)
    with pytest.raises(PermissionError):
        store.list_accounts(user,other_org)
    with pytest.raises(PermissionError):
        store.create_state(user,other_org,'browser')
    reconnect = dict(context,account_id=first)
    with pytest.raises(PermissionError):
        store.save_connection(reconnect,{'user_id':'222','username':'two'},'wrong-token',list(SCOPES),3600)
    with psycopg.connect(url) as connection:
        rows = connection.execute('SELECT account_id,encrypted_token FROM instagram_link.credentials').fetchall()
    tokens = {row[0]:Fernet(key).decrypt(bytes(row[1])).decode() for row in rows}
    assert tokens[first]=='token-one' and tokens[second]=='token-two'

    # Simulated revocation/expiry affects only one account and preserves ciphertext.
    before = store.credential_snapshot(first)
    other_before = store.credential_snapshot(second)
    assert store.apply_token_health(before, 'reconnect_required')
    assert store.credential_snapshot(first)['encrypted_token'] == before['encrypted_token']
    statuses = {a['id']: a['connection_status'] for a in store.list_accounts(user, org)}
    assert statuses[first] == 'reconnect_required' and statuses[second] == 'connected'
    # Valid reconnection uses the original identity and keeps history/account ID.
    reconnect_state = store.create_state(user, org, 'reconnect-browser', first)
    reconnect_context = store.consume_state(reconnect_state, 'reconnect-browser')
    assert store.save_connection(reconnect_context, {'user_id':'111'}, 'reconnected-token', list(SCOPES), 5184000) == first
    assert store.credential_snapshot(first)['token'] == 'reconnected-token'
    assert not store.apply_token_health(before, 'expired')
    assert not store.save_refreshed_token(before, 'stale-refresh-token', 5184000)
    fresh = store.credential_snapshot(first)
    assert store.save_refreshed_token(fresh, 'refreshed-token', 5184000)
    refreshed = store.credential_snapshot(first)
    assert refreshed['token'] == 'refreshed-token' and refreshed['paused']
    assert refreshed['encrypted_token'] != fresh['encrypted_token']
    assert store.credential_snapshot(second)['encrypted_token'] == other_before['encrypted_token']
    assert not store.apply_token_health(refreshed, 'provider_unavailable')
    assert store.apply_token_health(refreshed, 'expired')

    from datetime import datetime,timedelta,timezone
    from apps.api.m0_reply_store import SingleReplyStore,AUTHORIZATION_KEY
    store=SingleReplyStore(settings)
    monkeypatch.setattr(store,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    now=datetime.now(timezone.utc)
    def reserve_one(_):
        return store.reserve(first,'comment-one','media-one','recipient-one',now,now+timedelta(days=7))
    with ThreadPoolExecutor(max_workers=8) as executor:
        reservations=list(executor.map(reserve_one,range(40)))
    assert sum(reservations)==1
    with ThreadPoolExecutor(max_workers=8) as executor:
        claims=list(executor.map(lambda _:store.claim(),range(40)))
    assert sum(row is not None for row in claims)==1
    assert store.get()['attempt_count']==1
    store.finish({'status':'unknown','result_reason':'simulated_timeout'})
    assert store.claim() is None
    assert not store.reserve(second,'another-comment','other-media','other-recipient',now,now+timedelta(days=7))
    restarted=SingleReplyStore(settings)
    monkeypatch.setattr(restarted,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    assert restarted.claim() is None
    assert restarted.get()['status']=='unknown'
    # Crash persisted sending cannot return to reserved after lease expiry.
    with psycopg.connect(url) as connection:
        connection.execute("UPDATE instagram_link.m0_private_reply_attempts SET status='sending',dispatched_at=now()-interval '3 minutes' WHERE authorization_key=%s",(AUTHORIZATION_KEY,))
    assert restarted.claim() is None
    assert restarted.get()['status']=='unknown'
    assert restarted.get()['attempt_count']==1

    account_store = AccountStore(settings)
    monkeypatch.setattr(account_store,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    history = account_store.cockpit_history(user,org,first)
    assert history[0]['status']=='unknown'
    assert set(history[0]) == {'status','attempt_count','dispatched_at','finished_at','http_status'}
    assert account_store.cockpit_history(user,org,second)==[]
    with pytest.raises(PermissionError):
        account_store.cockpit_history(user,other_org,first)
    with pytest.raises(PermissionError):
        account_store.pause_account(user,other_org,first)
    with psycopg.connect(url) as c:
        c.execute('UPDATE instagram_link.instagram_accounts SET paused=false WHERE id=%s',(first,))
    assert account_store.pause_account(user,org,first)=={'paused':True}
    assert account_store.credential_snapshot(first)['paused']

    # Restore connection after the deliberate expiry test before creating a new automation.
    account_store.save_connection(context,{'user_id':'111','username':'one'},'catalog-reconnect-token',list(SCOPES),5184000)
    # Catalog persistence, immutable versions, organization/account isolation and reviews.
    from apps.api.catalog import CatalogStore,ConflictError
    catalog=CatalogStore(settings)
    monkeypatch.setattr(catalog,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    product=catalog.save_product(user,org,{'name':'Produto fictício','description':'','links':[{'label':'Comprar','url':'https://example.com/item'}],'active':True})
    catalog.save_publications(user,org,first,[{'id':'12345','caption':'Synthetic media','permalink':'https://www.instagram.com/p/synthetic/','media_type':'IMAGE','timestamp':now}])
    publication=catalog.publications(user,org,first)[0]
    data={'name':'Piloto fictício','product_id':product['id'],'publication_id':publication['id'],'include':['LINK'],'exclude':['não quero'],'ignore_accents':False,'template':'{{product_name}} {{product_links}}'}
    campaign=catalog.save_campaign(user,org,first,data)
    assert campaign['state']=='draft' and campaign['version']==1
    with pytest.raises(PermissionError):catalog.save_campaign(user,org,second,data)
    with pytest.raises(PermissionError):catalog.products(user,other_org)
    updated=catalog.save_product(user,org,{**product,'name':'Produto novo','expected_version':1},product['id'])
    assert updated['version']==2
    assert catalog.campaign(user,org,first,campaign['id'])['product_snapshot']['name']=='Produto fictício'
    with pytest.raises(ConflictError):catalog.save_product(user,org,{**product,'expected_version':1},product['id'])
    revision=catalog.save_campaign(user,org,first,{**data,'include':['QUERO'],'expected_version':1},campaign['id'])
    assert revision['version']==2
    with pytest.raises(ConflictError):catalog.save_campaign(user,org,first,{**data,'expected_version':1},campaign['id'])
    with pytest.raises(psycopg.Error):
        with psycopg.connect(url) as c:c.execute('UPDATE instagram_link.campaign_versions SET template=%s WHERE campaign_id=%s',('tamper',campaign['id']))
    review=catalog.save_review(user,org,first,campaign['id'],2,{'comments':[{'text':'private synthetic comment'}],'sending_enabled':False})
    with psycopg.connect(url) as c:
        encrypted=c.execute('SELECT encrypted_review FROM instagram_link.pilot_reviews WHERE id=%s',(review['id'],)).fetchone()[0]
    assert b'private synthetic comment' not in bytes(encrypted)
    assert catalog.campaign(user,org,first,campaign['id'])['state']=='paused'
    assert len(catalog.reviews(user,org,first))==1
    assert catalog.review_detail(user,org,first,review['id'])['comments'][0]['text']=='private synthetic comment'
    assert [v['version'] for v in catalog.versions(user,org,first,campaign['id'])]==[2,1]
    with pytest.raises(PermissionError):catalog.review_detail(user,org,second,review['id'])
    assert catalog.reviews(user,org,second)==[]
    with pytest.raises(ConflictError):catalog.save_review(user,org,first,campaign['id'],1,{})
    catalog.archive_campaign(user,org,first,campaign['id'],2)
    with pytest.raises(ValueError):catalog.save_campaign(user,org,first,{**data,'expected_version':2},campaign['id'])
    # Visual cache pagination: stable even for identical timestamps, scoped and encrypted.
    from datetime import timedelta
    extra=[{'id':str(70000+i),'caption':'Post '+str(i),'permalink':'https://www.instagram.com/p/test'+str(i)+'/', 'media_type':'IMAGE','media_url':'https://scontent.cdninstagram.com/image.jpg','timestamp':now-timedelta(days=i+1)} for i in range(28)]
    state=catalog.sync_state(user,org,first)
    catalog.save_publications(user,org,first,extra,sync_state=state,next_after='private-provider-cursor')
    with psycopg.connect(url) as c:
        raw=c.execute('SELECT publications_cursor FROM instagram_link.instagram_accounts WHERE id=%s',(first,)).fetchone()[0]
    assert b'private-provider-cursor' not in bytes(raw)
    assert catalog.sync_state(user,org,first)['after']=='private-provider-cursor'
    with pytest.raises(ConflictError):catalog.save_publications(user,org,first,[],sync_state=state,next_after=None)
    page=catalog.publications_page(user,org,first,limit=12)
    assert len(page['items'])==12 and page['next_cursor'] and page['has_more_remote']
    assert page['items'][0]['automations'][0]['id']==str(campaign['id'])
    with pytest.raises(ValueError):catalog.publications_page(user,org,second,page['next_cursor'])
    with pytest.raises(PermissionError):catalog.publications_page(user,other_org,first,page['next_cursor'])
    with pytest.raises(ValueError):catalog.publications_page(user,org,first,'tampered-cursor')
    ids={row['id'] for row in page['items']}
    while page['next_cursor']:
        page=catalog.publications_page(user,org,first,page['next_cursor'])
        assert not ids.intersection(row['id'] for row in page['items'])
        ids.update(row['id'] for row in page['items'])
    assert len(ids)==29
    # Two concurrent creates for one publication yield one draft; histories stay intact.
    concurrent_data={**data,'publication_id':catalog.publications(user,org,first)[1]['id']}
    from apps.api.catalog import PublicationInUse
    def create_draft():
        try:return catalog.save_campaign(user,org,first,concurrent_data)['id']
        except PublicationInUse:return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        created=list(executor.map(lambda _:create_draft(),range(2)))
    assert sum(value is not None for value in created)==1
    with pytest.raises(PublicationInUse):catalog.save_campaign(user,org,first,concurrent_data)
    # Supabase refresh serialized by DB row lock, encrypted at rest, identity checked.
    from apps.api.sessions import SessionStore
    session_store=SessionStore(settings)
    monkeypatch.setattr(session_store,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    refresh_calls=[]
    def auth_provider(method,path,**kwargs):
        if path=='user':return {'id':str(user),'email':'synthetic@example.invalid'}
        if 'refresh_token' in path:
            refresh_calls.append(1)
            return {'access_token':'renewed-synthetic-access','refresh_token':'renewed-synthetic-refresh','expires_in':3600}
        return {}
    monkeypatch.setattr(session_store,'provider',auth_provider)
    sid,created=session_store.create_verified({'access_token':'old-synthetic-access','refresh_token':'old-synthetic-refresh','expires_in':1})
    with ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda _:session_store.resolve(sid),range(5)))
    assert len(refresh_calls)==1 and all(r['user']['id']==str(user) for r in results)
    with psycopg.connect(url) as c:
        row=c.execute('SELECT session_hash,encrypted_session FROM instagram_link.cockpit_sessions').fetchone()
    assert row[0]!=sid and b'renewed-synthetic-refresh' not in bytes(row[1])
    assert b'renewed-synthetic-refresh' in Fernet(key).decrypt(bytes(row[1]))
    restarted_session=SessionStore(settings)
    monkeypatch.setattr(restarted_session,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    monkeypatch.setattr(restarted_session,'provider',auth_provider)
    assert restarted_session.resolve(sid)['csrf_token']==created['csrf_token']
    assert len(refresh_calls)==1
    session_store.remove(sid)
    from fastapi import HTTPException
    with pytest.raises(HTTPException):session_store.resolve(sid)

    # Provider expiry can precede our timestamp; recover via refresh, without login.
    resilient=SessionStore(settings)
    monkeypatch.setattr(resilient,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    phase={'initial':True,'rotated':0,'temporary':True}
    def resilient_provider(method,path,**kwargs):
        if method=='POST':
            phase['rotated']+=1
            return {'access_token':'recovery-access','refresh_token':'rotated-recovery-refresh','expires_in':3600}
        token=kwargs.get('headers',{}).get('Authorization')
        if not phase['initial'] and token=='Bearer original-recovery-access':raise HTTPException(401,'Synthetic provider expiry')
        if not phase['initial'] and phase['temporary']:
            phase['temporary']=False
            raise HTTPException(503,'Synthetic transient verification failure')
        return {'id':str(user)}
    monkeypatch.setattr(resilient,'provider',resilient_provider)
    recovery_sid,_=resilient.create_verified({'access_token':'original-recovery-access','refresh_token':'original-recovery-refresh','expires_in':3600})
    phase['initial']=False
    with pytest.raises(HTTPException) as temporary:resilient.resolve(recovery_sid)
    assert temporary.value.status_code==503
    assert resilient.resolve(recovery_sid)['user']['id']==str(user)
    assert phase['rotated']==1
    # Operational membership is organization-scoped; admin is never broadened.
    operator,viewer=uuid4(),uuid4()
    with psycopg.connect(url) as c:
        c.execute('INSERT INTO auth.users(id) VALUES (%s),(%s)',(operator,viewer))
        c.execute("INSERT INTO instagram_link.memberships(organization_id,user_id,role) VALUES (%s,%s,'viewer')",(org,viewer))
    assert account_store.grant_operator(user,org,operator)=={'role':'operator'}
    assert account_store.grant_operator(user,org,operator)=={'role':'operator'}
    with pytest.raises(ValueError):account_store.grant_operator(user,org,user)
    assert account_store.memberships(user)[0]['role']=='admin'
    with pytest.raises(PermissionError):account_store.grant_operator(operator,org,viewer)
    with pytest.raises(PermissionError):account_store.grant_operator(user,other_org,operator)
    operational_accounts=account_store.list_accounts(operator,org)
    assert len(operational_accounts)==2
    assert not {'ig_user_id','scopes','hourly_budget','cooldown_seconds'} & set(operational_accounts[0])
    with pytest.raises(PermissionError):account_store.list_accounts(operator,other_org)
    # OAuth permission is operational, but always bound to organization and account.
    for invalid_user,invalid_org in [(viewer,org),(operator,other_org)]:
        with pytest.raises(PermissionError):account_store.create_state(invalid_user,invalid_org,'denied')
    with pytest.raises(PermissionError):account_store.create_state(operator,other_org,'denied-target',first)
    original_first=account_store.credential_snapshot(first)
    original_second=account_store.credential_snapshot(second)
    op_state=account_store.create_state(operator,org,'operator-browser',first)
    with pytest.raises(PermissionError):account_store.consume_state(op_state,'other-browser')
    op_context=account_store.consume_state(op_state,'operator-browser')
    assert op_context['organization_id']==org and op_context['user_id']==operator and op_context['account_id']==first
    with pytest.raises(PermissionError):account_store.consume_state(op_state,'operator-browser')
    with pytest.raises(PermissionError):account_store.save_connection(op_context,{'user_id':'222'},'wrong-account',list(SCOPES),3600)
    assert account_store.save_connection(op_context,{'user_id':'111','username':'operator-reconnected'},'operator-new-token',list(SCOPES),3600)==first
    assert account_store.credential_snapshot(first)['paused']
    assert account_store.credential_snapshot(second)['encrypted_token']==original_second['encrypted_token']
    assert account_store.cockpit_history(operator,org,first)[0]['status']=='unknown'
    new_context=account_store.consume_state(account_store.create_state(operator,org,'new-account'),'new-account')
    third=account_store.save_connection(new_context,{'user_id':'333','username':'operator-added'},'operator-third-token',list(SCOPES),3600)
    assert account_store.credential_snapshot(third)['paused']
    with psycopg.connect(url) as c:
        row=c.execute('SELECT organization_id FROM instagram_link.instagram_accounts WHERE id=%s',(third,)).fetchone()
        encrypted=c.execute('SELECT encrypted_token FROM instagram_link.credentials WHERE account_id=%s',(third,)).fetchone()[0]
    assert row[0]==org and b'operator-third-token' not in bytes(encrypted)
    assert Fernet(key).decrypt(bytes(encrypted))==b'operator-third-token'
    # Recheck membership at both callback stages; revocation cannot be bypassed by old state.
    revoked=account_store.create_state(operator,org,'revoked')
    with psycopg.connect(url) as c:c.execute("UPDATE instagram_link.memberships SET role='viewer' WHERE user_id=%s AND organization_id=%s",(operator,org))
    with pytest.raises(PermissionError):account_store.consume_state(revoked,'revoked')
    with pytest.raises(PermissionError):account_store.save_connection(new_context,{'user_id':'333'},'revoked-token',list(SCOPES),3600)
    with psycopg.connect(url) as c:c.execute("UPDATE instagram_link.memberships SET role='operator' WHERE user_id=%s AND organization_id=%s",(operator,org))
    assert account_store.credential_snapshot(third)['token']=='operator-third-token'
    with pytest.raises(PermissionError):account_store.pause_account(operator,org,first)
    assert account_store.cockpit_history(operator,org,first)[0]['status']=='unknown'
    with pytest.raises(PermissionError):catalog.products(viewer,org)
    operational_product=catalog.save_product(operator,org,{'name':'Operação','description':'','links':[{'label':'Comprar','url':'https://example.com/operacao'}],'active':True})
    op_data={**data,'product_id':operational_product['id'],'name':'Campanha operacional'}
    op_campaign=catalog.save_campaign(operator,org,first,op_data)
    op_campaign=catalog.save_campaign(operator,org,first,{**op_data,'expected_version':1,'exclude':['CANCELAR']},op_campaign['id'])
    assert op_campaign['version']==2
    assert catalog.pause_campaign(operator,org,first,op_campaign['id'],2)=={'paused':True}
    assert catalog.campaign(operator,org,first,op_campaign['id'])['state']=='paused'
    assert len(catalog.versions(operator,org,first,op_campaign['id']))==2
    with pytest.raises(PermissionError):catalog.archive_campaign(operator,org,first,op_campaign['id'],2)
    with pytest.raises(PermissionError):catalog.pause_campaign(operator,other_org,first,op_campaign['id'],2)
    with pytest.raises(PermissionError):catalog.campaign(operator,org,second,op_campaign['id'])
    catalog.archive_product(operator,org,operational_product['id'],1)
    assert not next(p for p in catalog.products(operator,org) if p['id']==operational_product['id'])['active']
    # Admin in another organization must NOT confer admin here.
    with psycopg.connect(url) as c:
        c.execute("INSERT INTO instagram_link.memberships(organization_id,user_id,role) VALUES (%s,%s,'admin')",(other_org,operator))
    with account_store.connect() as c:
        with pytest.raises(PermissionError):account_store.require_admin(c,operator,org)
    foreign_context=account_store.consume_state(account_store.create_state(operator,other_org,'foreign'),'foreign')
    preserved=account_store.credential_snapshot(first)['encrypted_token']
    with pytest.raises(PermissionError):account_store.save_connection(foreign_context,{'user_id':'111'},'foreign-token',list(SCOPES),3600)
    with pytest.raises(PermissionError):account_store.create_state(operator,other_org,'foreign-target',first)
    assert account_store.credential_snapshot(first)['encrypted_token']==preserved
    # Force both organizations to see an absent ID before inserting: only one may win.
    from contextlib import contextmanager
    from threading import Barrier
    barrier=Barrier(2)
    race_store=AccountStore(settings)
    @contextmanager
    def race_connect():
        with psycopg.connect(url,row_factory=dict_row) as c:
            class Proxy:
                def execute(self,query,params=None):
                    result=c.execute(query,params)
                    if query.startswith('SELECT id,organization_id,ig_user_id'):
                        barrier.wait(timeout=10)
                    return result
            yield Proxy()
    monkeypatch.setattr(race_store,'connect',race_connect)
    def race(context,token):
        try:return race_store.save_connection(context,{'user_id':'concurrent-account'},token,list(SCOPES),3600)
        except PermissionError:return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs=[executor.submit(race,context,token) for context,token in [(new_context,'first-org-token'),(foreign_context,'other-org-token')]]
        outcomes=[job.result() for job in jobs]
    assert sum(value is not None for value in outcomes)==1
    winning=0 if outcomes[0] else 1
    with psycopg.connect(url) as c:
        row=c.execute('SELECT organization_id,paused FROM instagram_link.instagram_accounts WHERE ig_user_id=%s',('concurrent-account',)).fetchone()
    assert row==(org if winning==0 else other_org,True)
    assert account_store.credential_snapshot(outcomes[winning])['token']==['first-org-token','other-org-token'][winning]
    with account_store.connect() as c:account_store.require_admin(c,operator,other_org)
    # Verify actual HTTP routes against the actual SQL permission checks.
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from apps.api.auth import current_user
    from apps.api.main import create_app
    api_settings=replace(settings,instagram_app_id='12345',instagram_app_secret='synthetic-secret',meta_api_version='v26.0',redirect_uri='https://api.test/api/v1/instagram/callback')
    app=create_app(api_settings,inbox,account_store,catalog=catalog)
    app.dependency_overrides[current_user]=lambda:{'id':str(operator)}
    with TestClient(app,base_url='https://api.test') as client:
        params={'organization_id':str(org),'account_id':str(first)}
        assert client.get('/api/v1/instagram/accounts',params=params).status_code==200
        assert client.get('/api/v1/catalog/products',params=params).status_code==200
        assert client.get('/api/v1/catalog/campaigns',params=params).status_code==200
        assert client.get('/api/v1/instagram/history',params=params).status_code==200
        assert client.get('/api/v1/instagram/connect',params=params).status_code==200
        assert client.post('/api/v1/instagram/accounts/'+str(first)+'/pause',params=params).status_code==403
        async def fake_exchange(config,code):
            return {'user_id':'111','username':'operator-http'},'http-operator-token',list(SCOPES),3600
        async def fake_subscription(*args):return 'accepted'
        monkeypatch.setattr('apps.api.oauth_routes.exchange_code',fake_exchange)
        monkeypatch.setattr('apps.api.oauth_routes.subscribe_comments',fake_subscription)
        from urllib.parse import parse_qs,urlsplit
        authorization=client.get('/api/v1/instagram/connect',params=params)
        state=parse_qs(urlsplit(authorization.json()['authorization_url']).query)['state'][0]
        assert 'http-operator-token' not in authorization.text
        response=client.get('/api/v1/instagram/callback',params={'code':'synthetic-code','state':state,'organization_id':str(other_org)},follow_redirects=False)
        assert response.status_code==303 and 'http-operator-token' not in response.text+str(response.headers)
        assert client.get('/api/v1/instagram/callback',params={'code':'synthetic-code','state':state}).status_code==400
        assert account_store.credential_snapshot(first)['paused']
        assert next(a for a in account_store.list_accounts(operator,org) if a['id']==first)['comments_subscription_status']=='accepted'
        with psycopg.connect(url) as c:
            assert c.execute('SELECT organization_id FROM instagram_link.instagram_accounts WHERE id=%s',(first,)).fetchone()[0]==org

        assert client.get('/api/v1/catalog/products',params={'organization_id':str(other_org)}).status_code==200
        # Account still belongs to org, even when user has another membership.
        assert client.get('/api/v1/catalog/campaigns',params={'organization_id':str(other_org),'account_id':str(first)}).status_code==403
        sim=client.post('/api/v1/catalog/campaigns/'+str(op_campaign['id'])+'/simulate',params=params,json={'expected_version':2,'positive':'LINK','negative':'CANCELAR LINK'})
        assert sim.status_code==200 and sim.json()['valid'] and sim.json()['sending_enabled'] is False
    # Individual operator login uses Auth identity and DB memberships, not metadata roles.
    op_sessions=SessionStore(settings)
    monkeypatch.setattr(op_sessions,'connect',lambda:psycopg.connect(url,row_factory=dict_row))
    def op_provider(method,path,**kwargs):
        if path=='token?grant_type=password':
            assert kwargs['json']['password']=='individual-synthetic-password'
            return {'access_token':'operator-access','refresh_token':'operator-refresh','expires_in':3600}
        return {'id':str(operator),'email':'operator@example.invalid','user_metadata':{'role':'admin'}}
    monkeypatch.setattr(op_sessions,'provider',op_provider)
    op_sid,op_session=op_sessions.create_verified({'access_token':'operator-access','refresh_token':'operator-refresh','expires_in':3600})
    assert op_sessions.resolve(op_sid)['user']['id']==str(operator)
    assert op_sessions.update_password(op_sid,'chosen-strong-synthetic-password')=={'password_updated':True}
    # End-to-end cookie authentication + SQL authorization, with provider simulated only.
    cookie_app=create_app(replace(api_settings,public_app_url='https://api.test'),inbox,account_store,sessions=op_sessions,catalog=catalog)
    with TestClient(cookie_app,base_url='https://api.test') as client:
        login=client.post('/api/v1/auth/login',headers={'Origin':'https://api.test'},json={'email':'operator@example.invalid','password':'individual-synthetic-password'})
        assert login.status_code==200 and 'access_token' not in login.text
        assert client.get('/api/v1/catalog/products',params={'organization_id':str(org)}).status_code==200
        assert client.get('/api/v1/instagram/connect',params={'organization_id':str(org)}).status_code==200
        mutation={'Origin':'https://api.test','X-CSRF-Token':login.json()['csrf_token']}
        paused=client.post('/api/v1/catalog/campaigns/'+str(op_campaign['id'])+'/pause',params=params,headers=mutation,json={'expected_version':2})
        assert paused.status_code==200
        assert client.post('/api/v1/instagram/accounts/'+str(first)+'/pause',params=params,headers=mutation).status_code==403
        with psycopg.connect(url) as c:
            c.execute('DELETE FROM instagram_link.memberships WHERE user_id=%s AND organization_id=%s',(operator,org))
        assert client.get('/api/v1/catalog/products',params={'organization_id':str(org)}).status_code==403
    monkeypatch.setattr(op_sessions,'provider',lambda *a,**kw:{'id':str(viewer),'user_metadata':{'role':'admin'}})
    with pytest.raises(HTTPException):op_sessions.create_verified({'access_token':'viewer-access','refresh_token':'viewer-refresh','expires_in':3600})
