"""Database gate: authorization and comment unique; persist sending before HTTP."""
import hashlib
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
from cryptography.fernet import Fernet

AUTHORIZATION_KEY='m0-final-single-private-reply-2026-10-17'
MESSAGE='Teste M0 do MyAgentSales. Esta e a unica resposta privada deste teste.'


class SingleReplyStore:
    def __init__(self, settings):
        self.settings=settings
        self.cipher=Fernet(settings.encryption_key.encode())

    def connect(self):
        return psycopg.connect(self.settings.database_url,connect_timeout=10,sslmode='require',row_factory=dict_row)

    def get(self):
        with self.connect() as c:
            return c.execute('SELECT * FROM instagram_link.m0_private_reply_attempts WHERE authorization_key=%s',(AUTHORIZATION_KEY,)).fetchone()

    def reserve(self, account_id, comment_id, media_id, recipient_id, created_at, expires_at):
        with self.connect() as c:
            row=c.execute("INSERT INTO instagram_link.m0_private_reply_attempts(authorization_key,account_id,comment_id,media_id,recipient_id,comment_created_at,expires_at,encrypted_message,message_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING *",(AUTHORIZATION_KEY,account_id,comment_id,media_id,recipient_id,created_at,expires_at,self.cipher.encrypt(MESSAGE.encode()),hashlib.sha256(MESSAGE.encode()).hexdigest())).fetchone()
            return row is not None

    def claim(self):
        with self.connect() as c:
            # Any abandoned sending is terminal unknown, never available for resend.
            c.execute("UPDATE instagram_link.m0_private_reply_attempts SET status='unknown',result_reason='previous_dispatch_not_reconciled',finished_at=now() WHERE authorization_key=%s AND status='sending' AND dispatched_at<now()-interval '2 minutes'",(AUTHORIZATION_KEY,))
            row=c.execute("UPDATE instagram_link.m0_private_reply_attempts SET status='sending',attempt_count=1,attempt_id=%s,dispatched_at=now() WHERE authorization_key=%s AND status='reserved' AND attempt_count=0 AND expires_at>now()+interval '5 minutes' RETURNING *",(uuid4(),AUTHORIZATION_KEY)).fetchone()
            return row

    def finish(self, result):
        with self.connect() as c:
            c.execute("UPDATE instagram_link.m0_private_reply_attempts SET status=%s,finished_at=now(),http_status=%s,provider_message_id=%s,provider_recipient_id=%s,provider_error_code=%s,result_reason=%s WHERE authorization_key=%s AND attempt_count=1 AND status IN ('sending','unknown')",(result['status'],result.get('http_status'),result.get('provider_message_id'),result.get('provider_recipient_id'),result.get('provider_error_code'),result.get('result_reason'),AUTHORIZATION_KEY))
