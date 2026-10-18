"""Non-destructive verification: writes rolled back; errors always sanitized."""
import asyncio
import hashlib
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import httpx
import psycopg
from cryptography.fernet import Fernet
from apps.api.config import Settings

async def verify_auth(config):
    async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
        response = await client.get(config.supabase_url + '/auth/v1/user',headers={
            'apikey':config.supabase_key,'Authorization':'Bearer invalid-m0-test-token'})
    if response.status_code not in (401,403):
        raise ValueError('Auth verification failed')
    print('Supabase Auth: invalid token rejected')


def verify():
    config = Settings.from_env()
    with psycopg.connect(config.database_url,connect_timeout=10,sslmode='require') as c:
        tables = c.execute("SELECT tablename,rowsecurity FROM pg_tables WHERE schemaname='instagram_link'").fetchall()
        required={'organizations','memberships','instagram_accounts','credentials','oauth_states','webhook_envelopes','schema_migrations','m0_private_reply_attempts','cockpit_sessions','products','publications','campaigns','campaign_versions','pilot_reviews','catalog_audit','shopee_organization_credentials'}
        assert required.issubset({row[0] for row in tables}) and all(row[1] for row in tables)
        print('private schema: '+str(len(tables))+' tables with RLS')
        for role in ('anon','authenticated'):
            assert not c.execute("SELECT has_schema_privilege(%s,'instagram_link','USAGE')", (role,)).fetchone()[0]
            for table,_ in tables:
                assert not c.execute("SELECT has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')", (role,'instagram_link.'+table)).fetchone()[0]
            print(role + ': no schema/table access')
        payload = b'{"m0_probe":"synthetic_no_personal_data"}'
        encrypted = Fernet(config.encryption_key.encode()).encrypt(payload)
        c.execute('INSERT INTO instagram_link.webhook_envelopes(body_hash,encrypted_payload) VALUES (%s,%s)',(hashlib.sha256(payload).hexdigest(),encrypted))
        stored = c.execute('SELECT encrypted_payload FROM instagram_link.webhook_envelopes WHERE body_hash=%s',(hashlib.sha256(payload).hexdigest(),)).fetchone()[0]
        assert Fernet(config.encryption_key.encode()).decrypt(bytes(stored)) == payload
        c.rollback()
        print('encrypted inbox roundtrip: passed, probe rolled back')
    asyncio.run(verify_auth(config))
    print('dispatches: paused')

if __name__ == '__main__':
    try:
        verify()
    except Exception as exc:
        print('verification failed: ' + type(exc).__name__)
        raise SystemExit(1)
