-- One explicit M0 authorization, not a general dispatch queue.
CREATE TABLE instagram_link.m0_private_reply_attempts (
    authorization_key text PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES instagram_link.instagram_accounts(id),
    comment_id text NOT NULL,
    media_id text NOT NULL,
    recipient_id text NOT NULL,
    comment_created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    encrypted_message bytea NOT NULL,
    message_hash text NOT NULL,
    status text NOT NULL DEFAULT 'reserved' CHECK (status IN ('reserved','sending','accepted','failed','unknown')),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count BETWEEN 0 AND 1),
    attempt_id uuid UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    dispatched_at timestamptz,
    finished_at timestamptz,
    http_status integer,
    provider_message_id text,
    provider_recipient_id text,
    provider_error_code text,
    result_reason text,
    UNIQUE(account_id,comment_id),
    CHECK (expires_at>comment_created_at)
);
ALTER TABLE instagram_link.m0_private_reply_attempts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON instagram_link.m0_private_reply_attempts FROM PUBLIC, anon, authenticated;
