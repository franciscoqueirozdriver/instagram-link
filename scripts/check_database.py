"""Read-only diagnostics. Never print a DSN or raw exception."""
from pathlib import Path
import psycopg
from dotenv import dotenv_values

v = dotenv_values(Path(__file__).resolve().parents[1] / '.env.local')
try:
    with psycopg.connect(v['DATABASE_URL'], connect_timeout=10, sslmode='require') as c:
        print('connection: ok')
        for table in ('webhook_envelopes', 'instagram_accounts', 'credentials', 'schema_migrations', 'shopee_organization_credentials'):
            found = c.execute('SELECT to_regclass(%s) IS NOT NULL', ('instagram_link.' + table,)).fetchone()[0]
            print(table + ': ' + ('exists' if found else 'absent'))
        print('public_table_count:', c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'").fetchone()[0])
except Exception as e:
    print('connection_failed:', type(e).__name__)
    raise SystemExit(1)
