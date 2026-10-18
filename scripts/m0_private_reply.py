"""One authorized M0 attempt only. Default prepares; --execute consumes it.

No general processing, no network sends in --dedupe-check. Never print secrets.
"""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
import logging
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import httpx
import psycopg
from cryptography.fernet import Fernet
from apps.api.config import Settings
from apps.api.m0_reply_store import SingleReplyStore,AUTHORIZATION_KEY,MESSAGE
from packages.meta.private_reply import validate_text,send_once
from packages.meta.oauth import SCOPES
from packages.domain.timestamps import provider_timestamp

CONTROLLED_EVENT_RECEIVED='2026-10-17T04:41:50.182563+00:00'


def load_account(settings,account_id):
    from psycopg.rows import dict_row
    with psycopg.connect(settings.database_url,connect_timeout=10,sslmode='require',row_factory=dict_row) as c:
        row=c.execute('SELECT a.*,k.encrypted_token FROM instagram_link.instagram_accounts a JOIN instagram_link.credentials k ON k.account_id=a.id WHERE a.id=%s',(account_id,)).fetchone()
    if (not row or row['connection_status']!='connected' or row['expires_at']<=datetime.now(timezone.utc)
            or not set(SCOPES).issubset(set(row['scopes'])) or not row['paused']):
        raise ValueError('Connected paused account with valid permission/token required')
    token=Fernet(settings.encryption_key.encode()).decrypt(bytes(row['encrypted_token'])).decode()
    return row,token


def verify_target(settings,account,token,comment_id,media_id,recipient_id,created_at=None):
    root='https://graph.instagram.com/'+settings.meta_api_version
    with httpx.Client(timeout=20,follow_redirects=False,headers={'Authorization':'Bearer '+token}) as client:
        profile=client.get(root+'/me',params={'fields':'user_id,username'})
        profile.raise_for_status()
        if str(profile.json()['user_id'])!=account['ig_user_id']:
            raise ValueError('Token account mismatch')
        media_response=client.get(root+'/'+account['ig_user_id']+'/media',params={'fields':'id,permalink','limit':100})
        media_response.raise_for_status()
        media=next((item for item in media_response.json().get('data',[]) if str(item.get('id'))==media_id),None)
        if not media:
            raise ValueError('Media ownership unconfirmed')
        comment=client.get(root+'/'+comment_id,params={'fields':'id,from,text,timestamp,parent_id,hidden'})
        comment.raise_for_status();comment=comment.json()
        author=comment.get('from',{})
        if (str(comment.get('id'))!=comment_id or str(author.get('id'))!=recipient_id
                or recipient_id==account['ig_user_id'] or comment.get('parent_id') or comment.get('hidden') is not False):
            raise ValueError('Comment author/top-level/visibility not eligible')
        # Confirm the exact comment belongs to the intended owned media.
        page=client.get(root+'/'+media_id+'/comments',params={'fields':'id','limit':100})
        page.raise_for_status()
        if not any(str(item.get('id'))==comment_id for item in page.json().get('data',[])):
            raise ValueError('Exact comment not confirmed on media')
    timestamp=provider_timestamp(comment['timestamp'])
    if timestamp.tzinfo is None or (created_at and timestamp!=created_at):
        raise ValueError('Comment creation timestamp unconfirmed/changed')
    now=datetime.now(timezone.utc)
    if timestamp>now+timedelta(seconds=30) or now>=timestamp+timedelta(days=7,minutes=-5):
        raise ValueError('Comment outside private-reply window')
    return {'created_at':timestamp,'expires_at':timestamp+timedelta(days=7),
            'permalink':media['permalink'],'sender':profile.json().get('username'),
            'recipient':author.get('username')}


def prepare(settings,store):
    if store.get():
        print('Existing authorization reservation preserved; no new reservation/send.')
        return
    cipher=Fernet(settings.encryption_key.encode())
    with psycopg.connect(settings.database_url,connect_timeout=10,sslmode='require') as c:
        row=c.execute('SELECT encrypted_payload FROM instagram_link.webhook_envelopes WHERE received_at=%s',(CONTROLLED_EVENT_RECEIVED,)).fetchone()
        if not row:raise ValueError('Exact controlled real envelope missing')
        body=json.loads(cipher.decrypt(bytes(row[0])))
        changes=[(str(entry['id']),change['value']) for entry in body.get('entry',[]) for change in entry.get('changes',[]) if change.get('field')=='comments']
        if body.get('object')!='instagram' or len(changes)!=1:raise ValueError('Ambiguous controlled envelope')
        ig_id,value=changes[0]
        account_id=c.execute('SELECT id FROM instagram_link.instagram_accounts WHERE ig_user_id=%s',(ig_id,)).fetchone()[0]
    account,token=load_account(settings,account_id)
    comment_id=str(value['id']);media_id=str(value['media']['id']);recipient=str(value['from']['id'])
    target=verify_target(settings,account,token,comment_id,media_id,recipient)
    if not store.reserve(account_id,comment_id,media_id,recipient,target['created_at'],target['expires_at']):
        raise ValueError('Reservation collision; no send permitted')
    # These displays are explicitly requested test targets, never persisted to docs.
    print('prepared_sender:',target['sender']);print('prepared_recipient:',target['recipient'])
    print('prepared_publication:',target['permalink']);print('comment_id_suffix:',comment_id[-4:])
    print('comment_created_at_UTC:',target['created_at'].isoformat())
    print('message:',MESSAGE);print('UTF8_bytes:',len(MESSAGE.encode('utf-8')))
    print('Reservation committed; external_attempts: 0')


def execute(settings,store):
    plan=store.get()
    if not plan or plan['status']!='reserved' or plan['attempt_count']!=0:
        # May transition an abandoned sending to unknown; cannot claim terminal rows.
        if plan:store.claim()
        print('No unused reservation; external send blocked.')
        return
    account,token=load_account(settings,plan['account_id'])
    verify_target(settings,account,token,plan['comment_id'],plan['media_id'],plan['recipient_id'],plan['comment_created_at'])
    text=store.cipher.decrypt(bytes(plan['encrypted_message'])).decode()
    validate_text(text,settings.meta_max_message_length,settings.meta_message_length_unit)
    if text!=MESSAGE or hashlib.sha256(text.encode()).hexdigest()!=plan['message_hash']:
        raise ValueError('Message snapshot mismatch')
    # Atomically persist sending/attempt_count=1; commit finishes before HTTP.
    claimed=store.claim()
    if not claimed:
        print('Concurrent/duplicate attempt blocked; external sends: 0')
        return
    result=send_once(settings,account['ig_user_id'],plan['comment_id'],plan['recipient_id'],token,text)
    # A failure here leaves sending, still blocking resend; later recovery -> unknown.
    store.finish(result)
    print('single_attempt_result:',result['status'])
    print('meta_http_status:',result.get('http_status','unknown'))
    print('message_id_recorded:',bool(result.get('provider_message_id')))
    print('result_reason:',result['result_reason'])
    print('General processing remains paused; no automatic resend.')


def dedupe_check(store):
    plan=store.get()
    if not plan or plan['attempt_count']!=1 or plan['status']=='reserved':
        raise ValueError('Dispatch must already have consumed authorization')
    inserted=store.reserve(plan['account_id'],plan['comment_id'],plan['media_id'],plan['recipient_id'],plan['comment_created_at'],plan['expires_at'])
    claimed=store.claim()
    if inserted or claimed:raise ValueError('Duplicate gate failed')
    after=store.get()
    assert after['attempt_count']==1
    print('Local duplicate reservation/claim rejected; attempt_count=1; no HTTP send invoked.')


def main():
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--execute',action='store_true')
    group.add_argument('--dedupe-check',action='store_true')
    args=parser.parse_args()
    settings=Settings.from_env()
    if not settings.dispatches_paused:raise ValueError('General dispatch must remain paused')
    validate_text(MESSAGE,settings.meta_max_message_length,settings.meta_message_length_unit)
    store=SingleReplyStore(settings)
    if args.execute:execute(settings,store)
    elif args.dedupe_check:dedupe_check(store)
    else:prepare(settings,store)

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print('M0 stopped safely:',type(exc).__name__, '; do not resend automatically or delete reservation.')
        raise SystemExit(1)
