import os
from cryptography.fernet import Fernet
from apps.api.config import Settings


def test_explicit_file_loading_preserves_process_environment(tmp_path,monkeypatch):
    path=tmp_path/'.env.local'
    key=Fernet.generate_key().decode()
    path.write_text('\n'.join([
        'DATABASE_URL=postgresql://localhost/file', 'META_WEBHOOK_VERIFY_TOKEN=file-verify',
        'TOKEN_ENCRYPTION_KEY='+key,'INFRA_HEALTH_KEY=file-infra',
        'META_APP_ID=', 'META_APP_SECRET=', 'DISPATCHES_PAUSED=true',
        'SUPABASE_URL=https://project.supabase.co','SUPABASE_PUBLISHABLE_KEY=public-test',
        'META_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/instagram/callback']))
    for name in ['DATABASE_URL','META_WEBHOOK_VERIFY_TOKEN','TOKEN_ENCRYPTION_KEY','INFRA_HEALTH_KEY',
                 'META_INSTAGRAM_APP_ID','META_INSTAGRAM_APP_SECRET','META_APP_SECRET','META_APP_ID',
                 'META_WEBHOOK_APP_SECRET','DISPATCHES_PAUSED']:
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setattr('apps.api.config.ENV_FILE',path)
    monkeypatch.setenv('DATABASE_URL','postgresql://localhost/override')
    config=Settings.from_env()
    assert config.database_url.endswith('/override')
    assert config.encryption_key==key
    assert config.dispatches_paused
    assert not config.oauth_ready
