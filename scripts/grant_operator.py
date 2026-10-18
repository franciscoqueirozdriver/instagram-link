"""Trusted admin command: bind an Auth-invited user to one existing organization.
No signup, password, global permission, role overwrite or email/token logging.
"""
import argparse
import re
from pathlib import Path
import sys
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apps.api.accounts import AccountStore
from apps.api.config import Settings


def grant(email,organization_id,actor_id):
    email=email.strip()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Invalid email')
    store=AccountStore(Settings.from_env())
    with store.connect() as c:
        store.require_admin(c,actor_id,organization_id)
        users=c.execute('SELECT id FROM auth.users WHERE lower(email)=lower(%s)',(email,)).fetchall()
        if len(users)!=1:raise ValueError('Invite the user through Supabase Auth first')
        subject=users[0]['id']
    return store.grant_operator(actor_id,organization_id,subject)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--email-file',type=Path,required=True,help='Private file containing email; do not put email in shell history')
    parser.add_argument('--organization-id',type=UUID,required=True)
    parser.add_argument('--admin-user-id',type=UUID,required=True)
    args=parser.parse_args()
    try:
        result=grant(args.email_file.read_text(),args.organization_id,args.admin_user_id)
        print('Operator membership ready in the specified organization. Existing roles preserved.')
    except Exception as error:
        print('Operator access not granted:',type(error).__name__)
        raise SystemExit(1)
