"""Project-only migrations with checksum and advisory lock. No raw errors."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from apps.api.config import Settings


def migrate():
    config = Settings.from_env()
    with psycopg.connect(config.database_url, connect_timeout=10, sslmode='require') as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('instagram-link-migrations'))")
        c.execute('CREATE SCHEMA IF NOT EXISTS instagram_link')
        c.execute('REVOKE ALL ON SCHEMA instagram_link FROM PUBLIC, anon, authenticated')
        c.execute('CREATE TABLE IF NOT EXISTS instagram_link.schema_migrations '
                  '(name text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())')
        c.execute('ALTER TABLE instagram_link.schema_migrations ENABLE ROW LEVEL SECURITY')
        c.execute('REVOKE ALL ON instagram_link.schema_migrations FROM PUBLIC, anon, authenticated')
        for path in sorted((Path(__file__).resolve().parents[1] / 'db/migrations').glob('*.sql')):
            sql = path.read_text()
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            row = c.execute('SELECT checksum FROM instagram_link.schema_migrations WHERE name=%s', (path.name,)).fetchone()
            if row:
                if row[0] != checksum:
                    raise ValueError('Migration checksum mismatch')
                print(path.name + ': already applied')
                continue
            # Existing untracked M0 table needs manual reconciliation, never overwrite.
            if path.name.startswith('001') and c.execute("SELECT to_regclass('public.webhook_envelopes') IS NOT NULL OR to_regclass('instagram_link.webhook_envelopes') IS NOT NULL").fetchone()[0]:
                raise ValueError('Untracked inbox exists; reconcile before migrating')
            if path.name.startswith('001'):
                sql = sql.replace('BEGIN;', '').replace('COMMIT;', '')
            c.execute(sql)
            c.execute('INSERT INTO instagram_link.schema_migrations(name,checksum) VALUES (%s,%s)', (path.name,checksum))
            print(path.name + ': applied (commit at end)')
    print('migrations: committed')

if __name__ == '__main__':
    try:
        migrate()
    except Exception as exc:
        print('migrations: failed; transaction rolled back; category=' + type(exc).__name__)
        raise SystemExit(1)
