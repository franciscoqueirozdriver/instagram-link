"""Organization-scoped Shopee credentials; ciphertext never leaves the backend."""
import json

from apps.api.accounts import AccountStore


class ShopeeCredentialStore(AccountStore):
    def status(self, user_id, organization_id):
        with self.connect() as connection:
            self.require_admin(connection, user_id, organization_id)
            row = connection.execute(
                'SELECT configured_at,updated_at FROM instagram_link.shopee_organization_credentials WHERE organization_id=%s',
                (organization_id,),
            ).fetchone()
        return {
            'configured': row is not None,
            'configured_at': row['configured_at'] if row else None,
            'updated_at': row['updated_at'] if row else None,
        }

    def save(self, user_id, organization_id, app_id, app_secret):
        app_id = app_id.strip()
        app_secret = app_secret.strip()
        if not app_id or not app_secret:
            raise ValueError('Informe o App ID e o App Secret')
        encrypted = self.cipher.encrypt(json.dumps(
            {'app_id': app_id, 'app_secret': app_secret},
            separators=(',', ':'), ensure_ascii=False,
        ).encode())
        with self.connect() as connection:
            self.require_admin(connection, user_id, organization_id)
            connection.execute(
                'INSERT INTO instagram_link.shopee_organization_credentials(organization_id,encrypted_credentials,configured_by) '
                'VALUES (%s,%s,%s) ON CONFLICT(organization_id) DO UPDATE SET '
                'encrypted_credentials=EXCLUDED.encrypted_credentials,configured_by=EXCLUDED.configured_by,updated_at=now()',
                (organization_id, encrypted, user_id),
            )
        return {'configured': True}

    def credential_snapshot(self, user_id, organization_id):
        """Backend-only credential access; never serialize or log this result."""
        with self.connect() as connection:
            self.require_operator(connection, user_id, organization_id)
            row = connection.execute(
                'SELECT encrypted_credentials FROM instagram_link.shopee_organization_credentials WHERE organization_id=%s',
                (organization_id,),
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(self.cipher.decrypt(bytes(row['encrypted_credentials'])))
        except (ValueError, TypeError, KeyError):
            raise ValueError('Credencial Shopee indisponível') from None
        if not isinstance(payload, dict) or not all(isinstance(payload.get(key), str) and payload[key] for key in ('app_id', 'app_secret')):
            raise ValueError('Credencial Shopee indisponível')
        return payload
