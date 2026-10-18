import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[2] / '.env.local'


def configured(value):
    return bool(value) and not any(x in value.lower() for x in (
        'change_me', 'pendente', 'preencher', 'required_', '<', 'seu_', 'your_'))


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_secret: str
    verify_token: str
    encryption_key: str
    infra_key: str
    max_body_bytes: int = 1024 * 1024
    supabase_url: str = ''
    supabase_key: str = ''
    instagram_app_id: str = ''
    instagram_app_secret: str = ''
    meta_api_version: str = ''
    redirect_uri: str = 'http://localhost:8000/api/v1/instagram/callback'
    public_app_url: str = 'http://localhost:5173'
    dispatches_paused: bool = True
    privacy_controller_name: str = ''
    privacy_contact_email: str = ''
    privacy_contact_url: str = ''
    meta_max_message_length: int = 0
    meta_message_length_unit: str = ''
    cockpit_session_seconds: int = 604800

    def __post_init__(self):
        for name in ('database_url', 'verify_token', 'encryption_key', 'infra_key'):
            if not configured(getattr(self, name)):
                raise ValueError('Configuração obrigatória inválida: ' + name)
        if not 300 <= self.cockpit_session_seconds <= 2592000:
            raise ValueError('Invalid cockpit session lifetime')
        if self.app_secret and self.app_secret == self.verify_token:
            raise ValueError('Verify token deve ser independente do App Secret')
        Fernet(self.encryption_key.encode())
        if not self.dispatches_paused:
            raise ValueError('M0 exige DISPATCHES_PAUSED=true')

    @property
    def oauth_ready(self):
        u = urlsplit(self.redirect_uri)
        return (configured(self.instagram_app_id) and self.instagram_app_id.isdigit()
                and configured(self.instagram_app_secret)
                and bool(re.fullmatch(r'v\d+\.\d+', self.meta_api_version))
                and u.scheme == 'https' and bool(u.hostname))

    @classmethod
    def from_env(cls):
        load_dotenv(ENV_FILE, override=False, interpolate=False)
        get = lambda key: os.environ.get(key, '')
        # New names identify the Instagram product credentials explicitly.
        ig_secret = get('META_INSTAGRAM_APP_SECRET') or get('META_APP_SECRET')
        return cls(
            database_url=get('DATABASE_URL'), app_secret=get('META_WEBHOOK_APP_SECRET'),
            verify_token=get('META_WEBHOOK_VERIFY_TOKEN'), encryption_key=get('TOKEN_ENCRYPTION_KEY'),
            infra_key=get('INFRA_HEALTH_KEY'), supabase_url=get('SUPABASE_URL').rstrip('/'),
            supabase_key=get('SUPABASE_PUBLISHABLE_KEY'),
            instagram_app_id=get('META_INSTAGRAM_APP_ID') or get('META_APP_ID'),
            instagram_app_secret=ig_secret, meta_api_version=get('META_API_VERSION'),
            redirect_uri=get('META_OAUTH_REDIRECT_URI'), public_app_url=get('PUBLIC_APP_URL'),
            dispatches_paused=get('DISPATCHES_PAUSED').lower() == 'true',
            privacy_controller_name=get('PRIVACY_CONTROLLER_NAME'),
            privacy_contact_email=get('PRIVACY_CONTACT_EMAIL'),
            privacy_contact_url=get('PRIVACY_CONTACT_URL'),
            meta_max_message_length=int(get('META_MAX_MESSAGE_LENGTH') or '0'),
            meta_message_length_unit=get('META_MESSAGE_LENGTH_UNIT'),
            cockpit_session_seconds=int(get('COCKPIT_SESSION_SECONDS') or '604800'))
