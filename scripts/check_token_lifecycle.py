"""Default read-only; --refresh rotates eligible Instagram tokens, never sends."""
import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from apps.api.accounts import AccountStore
from apps.api.config import Settings
from packages.meta.token_lifecycle import checked_payload, refresh_eligibility, refresh_token

async def check(do_refresh=False):
    logging.getLogger('httpx').setLevel(logging.WARNING)
    config = Settings.from_env()
    assert config.dispatches_paused
    store = AccountStore(config)
    with store.connect() as c:
        ids = [r['id'] for r in c.execute('SELECT id FROM instagram_link.instagram_accounts').fetchall()]
    async with httpx.AsyncClient(timeout=20, follow_redirects=False, transport=httpx.AsyncHTTPTransport(retries=0)) as client:
        for index, account_id in enumerate(ids, 1):
            s = store.credential_snapshot(account_id)
            assert s and s['paused']
            profile = checked_payload(await client.get('https://graph.instagram.com/'+config.meta_api_version+'/me', params={'fields':'user_id'}, headers={'Authorization':'Bearer '+s['token']}))
            assert str(profile.get('user_id')) == s['ig_user_id']
            now = datetime.now(timezone.utc)
            eligible = refresh_eligibility(s['refreshed_at'], s['expires_at'], now, s['scopes'])
            assert store.credential_snapshot(account_id)['encrypted_token'] == s['encrypted_token']
            print('account', index, ': identity valid; paused; ciphertext unchanged; refresh:', eligible)
            print('earliest_refresh_utc:', (s['refreshed_at']+timedelta(hours=24)).isoformat())
            if do_refresh and eligible == 'eligible':
                token, seconds = await refresh_token(config, s, now, client)
                assert store.save_refreshed_token(s, token, seconds), 'Concurrent credential change'
                print('refresh: identity checked; encrypted token updated atomically; still paused')
            elif do_refresh:
                print('refresh skipped:', eligible)
    print('No revocation, OAuth or messages request performed. Refresh only when requested and eligible.')

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--refresh', action='store_true', help='Refresh only eligible long-lived Instagram tokens')
        asyncio.run(check(parser.parse_args().refresh))
    except Exception as error:
        print('Lifecycle check failed:', type(error).__name__)
        sys.exit(1)
