import hashlib

import psycopg
from cryptography.fernet import Fernet


class PostgresInbox:
    def __init__(self, database_url: str, encryption_key: str):
        self.database_url = database_url
        self.cipher = Fernet(encryption_key.encode())

    def save(self, body: bytes) -> None:
        encrypted = self.cipher.encrypt(body)
        # Sair do contexto confirma a transação antes do ACK HTTP.
        with psycopg.connect(self.database_url, connect_timeout=3) as connection:
            connection.execute(
                'INSERT INTO instagram_link.webhook_envelopes (body_hash, encrypted_payload) '
                'VALUES (%s, %s) ON CONFLICT (body_hash) DO NOTHING',
                (hashlib.sha256(body).hexdigest(), encrypted),
            )

    def ready(self) -> None:
        with psycopg.connect(self.database_url, connect_timeout=3) as connection:
            connection.execute('SELECT id FROM instagram_link.webhook_envelopes LIMIT 0')
