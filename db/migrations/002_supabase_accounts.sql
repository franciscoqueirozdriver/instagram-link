CREATE SCHEMA IF NOT EXISTS instagram_link;
REVOKE ALL ON SCHEMA instagram_link FROM PUBLIC, anon, authenticated;
CREATE TABLE instagram_link.organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    paused boolean NOT NULL DEFAULT true
);
CREATE TABLE instagram_link.memberships (
    organization_id uuid NOT NULL REFERENCES instagram_link.organizations(id),
    user_id uuid NOT NULL REFERENCES auth.users(id),
    role text NOT NULL CHECK (role IN ('admin','operator','viewer')),
    PRIMARY KEY (organization_id,user_id)
);
CREATE TABLE instagram_link.instagram_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES instagram_link.organizations(id),
    ig_user_id text NOT NULL UNIQUE,
    username text,
    display_name text,
    connection_status text NOT NULL CHECK (connection_status IN ('pending','connected','expiring','reconnect_required','disconnected')),
    scopes jsonb NOT NULL DEFAULT '[]',
    expires_at timestamptz,
    paused boolean NOT NULL DEFAULT true,
    hourly_budget integer NOT NULL DEFAULT 600 CHECK (hourly_budget BETWEEN 1 AND 600),
    cooldown_seconds integer NOT NULL DEFAULT 86400 CHECK (cooldown_seconds >= 86400),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id,organization_id)
);
CREATE TABLE instagram_link.credentials (
    account_id uuid PRIMARY KEY REFERENCES instagram_link.instagram_accounts(id),
    encrypted_token bytea NOT NULL,
    key_version integer NOT NULL DEFAULT 1,
    refreshed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE instagram_link.oauth_states (
    state_hash text PRIMARY KEY,
    browser_hash text NOT NULL,
    user_id uuid NOT NULL REFERENCES auth.users(id),
    organization_id uuid NOT NULL REFERENCES instagram_link.organizations(id),
    account_id uuid,
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '10 minutes'),
    consumed_at timestamptz,
    FOREIGN KEY (account_id,organization_id) REFERENCES instagram_link.instagram_accounts(id,organization_id)
);
DO $$
DECLARE item text;
BEGIN
    FOREACH item IN ARRAY ARRAY['organizations','memberships','instagram_accounts','credentials','oauth_states'] LOOP
        EXECUTE format('ALTER TABLE instagram_link.%I ENABLE ROW LEVEL SECURITY', item);
        EXECUTE format('REVOKE ALL ON TABLE instagram_link.%I FROM PUBLIC, anon, authenticated', item);
    END LOOP;
END $$;
-- No public policies. Backend connects via DATABASE_URL with a server role.
ALTER TABLE public.webhook_envelopes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.webhook_envelopes FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE public.webhook_envelopes_id_seq FROM PUBLIC, anon, authenticated;
ALTER TABLE public.webhook_envelopes SET SCHEMA instagram_link;
