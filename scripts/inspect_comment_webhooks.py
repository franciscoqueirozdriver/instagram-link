"""Read-only inspection of encrypted inbox; prints counts, never payload/text/IDs.

The HTTP ingestion route enforces raw-body HMAC before saving. Historical rows
have no signature header stored, so this script does not independently reverify it.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import psycopg
from cryptography.fernet import Fernet
from apps.api.config import Settings, configured


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--since',required=True,help='UTC timestamp before controlled comment')
    args=parser.parse_args()
    since=datetime.fromisoformat(args.since.replace('Z','+00:00'))
    if since.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    settings=Settings.from_env()
    if not configured(settings.app_secret):
        print('Webhook signing secret absent: real POST validation blocked.')
        return
    cipher=Fernet(settings.encryption_key.encode())
    with psycopg.connect(settings.database_url,connect_timeout=10,sslmode='require') as c:
        rows=c.execute('SELECT encrypted_payload FROM instagram_link.webhook_envelopes WHERE received_at>=%s ORDER BY received_at DESC LIMIT 100',(since,)).fetchall()
    comments=0
    for row in rows:
        body=json.loads(cipher.decrypt(bytes(row[0])))
        if not isinstance(body,dict) or body.get('object')!='instagram':
            continue
        for entry in body.get('entry',[]):
            if not isinstance(entry,dict):continue
            for change in entry.get('changes',[]):
                if isinstance(change,dict) and change.get('field')=='comments':
                    comments+=1
    print('envelopes_since_controlled_test:',len(rows))
    print('instagram_comments_changes:',comments)
    print('dispatches_paused:',settings.dispatches_paused)
    print('Note: distinguish real comments from dashboard synthetic tests using controlled timing.')

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print('Inspection failed:',type(exc).__name__)
        raise SystemExit(1)
