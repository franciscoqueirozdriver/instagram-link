"""Fill only absent/placeholders; do not print values."""
import os
import secrets
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from cryptography.fernet import Fernet
from dotenv import dotenv_values

p = Path(__file__).resolve().parents[1] / '.env.local'
v = dict(dotenv_values(p))

def pending(value):
    return not value or any(x in value.lower() for x in ('change_me', 'pendente', 'preencher', 'required_', '<', 'seu_', 'your_'))

def put(key, value, force=False):
    if not force and not pending(v.get(key)):
        return
    lines = p.read_text().splitlines()
    line = key + "='" + value.replace("'", "\\'") + "'"
    matches = [i for i, old in enumerate(lines) if old.split('=', 1)[0].strip() == key]
    if matches:
        lines[matches[-1]] = line
    else:
        lines.append(line)
    p.write_text('\n'.join(lines) + '\n')
    v[key] = value

put('TOKEN_ENCRYPTION_KEY', Fernet.generate_key().decode())
# Invalid existing key is never replaced automatically.
Fernet(v['TOKEN_ENCRYPTION_KEY'].encode())
put('META_WEBHOOK_VERIFY_TOKEN', secrets.token_urlsafe(48))
put('INFRA_HEALTH_KEY', secrets.token_urlsafe(48))
put('API_PUBLIC_URL', 'http://localhost:8000')
put('PUBLIC_APP_URL', 'http://localhost:5173')
put('META_OAUTH_REDIRECT_URI', v['API_PUBLIC_URL'].rstrip('/') + '/api/v1/instagram/callback')
put('DISPATCHES_PAUSED', 'true', force=True)
# Escape URI delimiters in the existing password, preserving its value.
u = urlsplit(v['DATABASE_URL'])
if u.username and u.password and u.hostname:
    host = '[' + u.hostname + ']' if ':' in u.hostname else u.hostname
    netloc = quote(unquote(u.username), safe='') + ':' + quote(unquote(u.password), safe='') + '@' + host
    if u.port:
        netloc += ':' + str(u.port)
    put('DATABASE_URL', urlunsplit((u.scheme, netloc, u.path, u.query, u.fragment)), force=True)
os.chmod(p, 0o600)
print('Configuração local atualizada; valores preservados, chaves ausentes geradas, envios pausados.')
