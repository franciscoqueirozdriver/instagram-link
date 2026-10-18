-- M0: inbox de quarentena. Não produz eventos nem dispara mensagens.
BEGIN;
CREATE TABLE webhook_envelopes (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    received_at timestamptz NOT NULL DEFAULT now(),
    body_hash text NOT NULL UNIQUE CHECK (length(body_hash) = 64),
    encrypted_payload bytea NOT NULL,
    processing_state text NOT NULL DEFAULT 'pending_validation'
        CHECK (processing_state IN ('pending_validation', 'processed', 'unsupported')),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '7 days')
);
CREATE INDEX webhook_envelopes_expiry ON webhook_envelopes (expires_at);
COMMIT;
