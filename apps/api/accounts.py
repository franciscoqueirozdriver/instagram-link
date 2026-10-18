import hashlib
import hmac
import secrets

import psycopg
from cryptography.fernet import Fernet
from psycopg.rows import dict_row


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class AccountStore:
    def __init__(self, settings):
        self.settings = settings
        self.cipher = Fernet(settings.encryption_key.encode())

    def connect(self):
        return psycopg.connect(self.settings.database_url, connect_timeout=10, sslmode='require', row_factory=dict_row)

    def memberships(self, user_id):
        with self.connect() as c:
            return c.execute('SELECT organization_id,role FROM instagram_link.memberships WHERE user_id=%s', (user_id,)).fetchall()

    def require_admin(self, c, user_id, org_id):
        row = c.execute("SELECT role FROM instagram_link.memberships WHERE user_id=%s AND organization_id=%s FOR SHARE", (user_id, org_id)).fetchone()
        if not row or row['role'] != 'admin':
            raise PermissionError()

    def require_operator(self, c, user_id, org_id):
        """Operational membership in THIS organization; never a global role."""
        row = c.execute("SELECT role FROM instagram_link.memberships WHERE user_id=%s AND organization_id=%s FOR SHARE", (user_id, org_id)).fetchone()
        if not row or row['role'] not in ('admin', 'operator'):
            raise PermissionError()
        return row['role']

    def grant_operator(self, actor_id, org_id, subject_id):
        """Trusted admin provisioning only. Never overwrite an existing role."""
        with self.connect() as c:
            self.require_admin(c, actor_id, org_id)
            if not c.execute('SELECT id FROM auth.users WHERE id=%s', (subject_id,)).fetchone():
                raise ValueError('Existing Supabase Auth user required')
            c.execute("INSERT INTO instagram_link.memberships(organization_id,user_id,role) VALUES (%s,%s,'operator') ON CONFLICT DO NOTHING", (org_id,subject_id))
            role=c.execute('SELECT role FROM instagram_link.memberships WHERE organization_id=%s AND user_id=%s', (org_id,subject_id)).fetchone()['role']
            if role != 'operator':
                raise ValueError('Existing role preserved; explicit role change required')
            return {'role': 'operator'}

    def list_accounts(self, user_id, org_id):
        with self.connect() as c:
            role = self.require_operator(c, user_id, org_id)
            columns = ('id,ig_user_id,username,display_name,connection_status,scopes,expires_at,paused,hourly_budget,cooldown_seconds,comments_subscription_status,comments_subscribed_at'
                       if role == 'admin' else 'id,username,display_name,connection_status,expires_at,paused,comments_subscription_status')
            return c.execute('SELECT '+columns+' FROM instagram_link.instagram_accounts WHERE organization_id=%s ORDER BY created_at', (org_id,)).fetchall()

    def create_state(self, user_id, org_id, browser, account_id=None):
        state = secrets.token_urlsafe(48)
        with self.connect() as c:
            self.require_operator(c, user_id, org_id)
            if account_id and not c.execute('SELECT id FROM instagram_link.instagram_accounts WHERE id=%s AND organization_id=%s', (account_id,org_id)).fetchone():
                raise PermissionError()
            c.execute('INSERT INTO instagram_link.oauth_states(state_hash,browser_hash,user_id,organization_id,account_id) VALUES (%s,%s,%s,%s,%s)', (digest(state),digest(browser),user_id,org_id,account_id))
        return state

    def consume_state(self, state, browser):
        with self.connect() as c:
            # Commit consumption before calling the external provider: single use even on failure.
            row = c.execute('UPDATE instagram_link.oauth_states SET consumed_at=now() WHERE state_hash=%s AND browser_hash=%s AND consumed_at IS NULL AND expires_at>now() RETURNING user_id,organization_id,account_id', (digest(state),digest(browser))).fetchone()
            if not row:
                raise PermissionError()
            self.require_operator(c, row['user_id'], row['organization_id'])
            return row

    def save_connection(self, context, profile, token, scopes, expires_in):
        from datetime import datetime, timedelta, timezone
        from psycopg.types.json import Jsonb
        expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        with self.connect() as c:
            self.require_operator(c,context['user_id'],context['organization_id'])
            existing = c.execute('SELECT id,organization_id,ig_user_id FROM instagram_link.instagram_accounts WHERE ig_user_id=%s FOR UPDATE', (profile['user_id'],)).fetchone()
            if existing and existing['organization_id'] != context['organization_id']:
                raise PermissionError()
            if context['account_id']:
                target = c.execute('SELECT ig_user_id FROM instagram_link.instagram_accounts WHERE id=%s AND organization_id=%s FOR UPDATE', (context['account_id'],context['organization_id'])).fetchone()
                if not target or target['ig_user_id'] != profile['user_id']:
                    raise PermissionError()
            row = c.execute("INSERT INTO instagram_link.instagram_accounts(organization_id,ig_user_id,username,connection_status,scopes,expires_at) VALUES (%s,%s,%s,'connected',%s,%s) ON CONFLICT(ig_user_id) DO UPDATE SET username=EXCLUDED.username,connection_status='connected',scopes=EXCLUDED.scopes,expires_at=EXCLUDED.expires_at,updated_at=now(),paused=true WHERE instagram_accounts.organization_id=EXCLUDED.organization_id RETURNING id", (context['organization_id'], profile['user_id'],profile.get('username'),Jsonb(scopes),expires)).fetchone()
            if not row:raise PermissionError()  # Conflicting concurrent insert belongs to another organization.
            c.execute('INSERT INTO instagram_link.credentials(account_id,encrypted_token) VALUES (%s,%s) ON CONFLICT(account_id) DO UPDATE SET encrypted_token=EXCLUDED.encrypted_token,refreshed_at=now()', (row['id'],self.cipher.encrypt(token.encode())))
            stored = c.execute('SELECT encrypted_token FROM instagram_link.credentials WHERE account_id=%s',(row['id'],)).fetchone()
            if not hmac.compare_digest(self.cipher.decrypt(bytes(stored['encrypted_token'])),token.encode()):
                raise ValueError('Credential verification failed')
            return row['id']

    def subscription_result(self, account_id, status):
        if status not in ('failed','accepted','confirmed'):
            raise ValueError('Invalid subscription status')
        with self.connect() as c:
            c.execute("UPDATE instagram_link.instagram_accounts SET comments_subscription_status=%s, comments_subscribed_at=CASE WHEN %s IN ('accepted','confirmed') THEN now() ELSE NULL END, updated_at=now() WHERE id=%s", (status,status,account_id))

    def credential_snapshot(self, account_id):
        """Backend only; callers must never serialize/log this snapshot."""
        with self.connect() as c:
            row = c.execute('SELECT a.id,a.ig_user_id,a.scopes,a.expires_at,a.paused,c.encrypted_token,c.refreshed_at FROM instagram_link.instagram_accounts a JOIN instagram_link.credentials c ON c.account_id=a.id WHERE a.id=%s', (account_id,)).fetchone()
            if row:
                row['encrypted_token'] = bytes(row['encrypted_token'])
                row['token'] = self.cipher.decrypt(row['encrypted_token']).decode()
            return row

    def apply_token_health(self, snapshot, reason):
        """Stale checks cannot pause a newly reconnected account; retain ciphertext."""
        if reason not in ('expired', 'reconnect_required', 'permission_denied', 'missing_permission'):
            return False
        with self.connect() as c:
            c.execute('SELECT id FROM instagram_link.instagram_accounts WHERE id=%s FOR UPDATE', (snapshot['id'],)).fetchone()
            row = c.execute("UPDATE instagram_link.instagram_accounts a SET connection_status='reconnect_required',paused=true,updated_at=now() FROM instagram_link.credentials c WHERE a.id=%s AND c.account_id=a.id AND c.encrypted_token=%s RETURNING a.id", (snapshot['id'], snapshot['encrypted_token'])).fetchone()
            return row is not None

    def save_refreshed_token(self, snapshot, token, expires_in):
        from datetime import datetime, timedelta, timezone
        if not token or type(expires_in) is not int or expires_in <= 0:
            raise ValueError('Invalid refresh result')
        with self.connect() as c:
            # Same lock order as reconnection: account before credential.
            c.execute('SELECT id FROM instagram_link.instagram_accounts WHERE id=%s FOR UPDATE', (snapshot['id'],)).fetchone()
            row = c.execute('UPDATE instagram_link.credentials SET encrypted_token=%s,refreshed_at=now() WHERE account_id=%s AND encrypted_token=%s RETURNING account_id', (self.cipher.encrypt(token.encode()), snapshot['id'], snapshot['encrypted_token'])).fetchone()
            if not row:
                return False
            c.execute("UPDATE instagram_link.instagram_accounts SET expires_at=%s,connection_status='connected',paused=true,updated_at=now() WHERE id=%s", (datetime.now(timezone.utc)+timedelta(seconds=expires_in),snapshot['id']))
            return True

    def cockpit_history(self, user_id, org_id, account_id):
        with self.connect() as c:
            self.require_operator(c, user_id, org_id)
            if not c.execute('SELECT id FROM instagram_link.instagram_accounts WHERE id=%s AND organization_id=%s', (account_id, org_id)).fetchone():
                raise PermissionError()
            return c.execute('SELECT status,attempt_count,dispatched_at,finished_at,http_status FROM instagram_link.m0_private_reply_attempts WHERE account_id=%s ORDER BY created_at DESC LIMIT 50', (account_id,)).fetchall()

    def pause_account(self, user_id, org_id, account_id):
        with self.connect() as c:
            self.require_admin(c, user_id, org_id)
            row = c.execute('UPDATE instagram_link.instagram_accounts SET paused=true,updated_at=now() WHERE id=%s AND organization_id=%s RETURNING id', (account_id, org_id)).fetchone()
            if not row:
                raise PermissionError()
            return {'paused': True}
