"""Bind an existing Supabase Auth user; no public signup or password handling."""
import argparse
from pathlib import Path
import sys
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from apps.api.config import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user-id',required=True,type=UUID)
    parser.add_argument('--organization-name',default='Instagram Link')
    args = parser.parse_args()
    settings = Settings.from_env()
    with psycopg.connect(settings.database_url,connect_timeout=10,sslmode='require') as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('instagram-link-bootstrap'))")
        if c.execute('SELECT EXISTS(SELECT 1 FROM instagram_link.memberships)').fetchone()[0]:
            raise ValueError('Bootstrap already completed')
        if not c.execute('SELECT id FROM auth.users WHERE id=%s',(args.user_id,)).fetchone():
            raise ValueError('Existing Auth user required')
        org = c.execute('INSERT INTO instagram_link.organizations(name) VALUES (%s) RETURNING id',(args.organization_name,)).fetchone()[0]
        c.execute("INSERT INTO instagram_link.memberships(organization_id,user_id,role) VALUES (%s,%s,'admin')",(org,args.user_id))
    print('Bootstrap administrativo concluído; organização pausada.')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Bootstrap não aplicado: '+type(exc).__name__)
        raise SystemExit(1)
