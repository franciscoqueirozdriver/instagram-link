"""Process-local counters only. No payload, signature, token, IP or account ID."""
from datetime import datetime, timezone


class WebhookDiagnostics:
    OUTCOMES = ('persisted', 'invalid_signature', 'missing_secret', 'payload_too_large', 'storage_unavailable')

    def __init__(self):
        self.data = {'started_at': self.now(), 'received': 0,
                     'last_received_at': None, 'last_outcome': None,
                     'rejected_matches_instagram_oauth_secret': 0,
                     'verification_received': 0, 'verification_accepted': 0,
                     'verification_rejected': 0, 'verification_last_at': None,
                     'verification_last_outcome': None,
                     **{name: 0 for name in self.OUTCOMES}}

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def observe(self):
        self.data['received'] += 1
        self.data['last_received_at'] = self.now()

    def decide(self, outcome):
        if outcome not in self.OUTCOMES:
            raise ValueError('Unknown diagnostic outcome')
        self.data[outcome] += 1
        self.data['last_outcome'] = outcome

    def note_oauth_match_on_rejection(self):
        # Evidence only: never affects authorization or persistence.
        self.data['rejected_matches_instagram_oauth_secret'] += 1

    def verification(self, outcome):
        if outcome not in ('accepted', 'invalid_mode', 'missing_challenge', 'token_mismatch'):
            raise ValueError('Unknown verification outcome')
        self.data['verification_received'] += 1
        self.data['verification_accepted' if outcome == 'accepted' else 'verification_rejected'] += 1
        self.data['verification_last_at'] = self.now()
        self.data['verification_last_outcome'] = outcome

    def snapshot(self):
        return dict(self.data)
