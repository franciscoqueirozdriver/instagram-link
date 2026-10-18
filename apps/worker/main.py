"""Paused M0 worker: validates shared configuration/storage; never sends."""
from apps.api.config import Settings
from apps.api.inbox import PostgresInbox


def main():
    settings = Settings.from_env()  # Explicit absolute .env.local, same as API.
    PostgresInbox(settings.database_url,settings.encryption_key).ready()
    print('Worker M0: banco disponível; envios pausados; nenhum job despachado.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Worker M0: configuração ou banco indisponível; envios bloqueados.')
        raise SystemExit(1)
