CREATE TABLE instagram_link.cockpit_sessions (
 session_hash text PRIMARY KEY, user_id uuid NOT NULL REFERENCES auth.users(id),
 encrypted_session bytea NOT NULL, access_expires_at timestamptz NOT NULL,
 csrf_token text NOT NULL, expires_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE instagram_link.products (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), organization_id uuid NOT NULL REFERENCES instagram_link.organizations(id),
 name text NOT NULL CHECK(length(name) BETWEEN 1 AND 160), description text NOT NULL DEFAULT '',
 links jsonb NOT NULL CHECK(jsonb_typeof(links)='array'), active boolean NOT NULL DEFAULT true,
 version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(id,organization_id)
);
CREATE TABLE instagram_link.publications (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), organization_id uuid NOT NULL, account_id uuid NOT NULL,
 ig_media_id text NOT NULL, caption text NOT NULL DEFAULT '', permalink text NOT NULL,
 media_type text NOT NULL, published_at timestamptz NOT NULL, synced_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(account_id,organization_id) REFERENCES instagram_link.instagram_accounts(id,organization_id),
 UNIQUE(account_id,ig_media_id), UNIQUE(id,account_id,organization_id)
);
CREATE TABLE instagram_link.campaigns (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), organization_id uuid NOT NULL, account_id uuid NOT NULL,
 publication_id uuid NOT NULL, product_id uuid NOT NULL, name text NOT NULL CHECK(length(name) BETWEEN 1 AND 160),
 state text NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','paused','archived')),
 version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(publication_id,account_id,organization_id) REFERENCES instagram_link.publications(id,account_id,organization_id),
 FOREIGN KEY(product_id,organization_id) REFERENCES instagram_link.products(id,organization_id),
 UNIQUE(id,organization_id)
);
CREATE TABLE instagram_link.campaign_versions (
 campaign_id uuid NOT NULL REFERENCES instagram_link.campaigns(id), version integer NOT NULL,
 rules jsonb NOT NULL, product_snapshot jsonb NOT NULL, template text NOT NULL,
 rendered_message text NOT NULL, created_by uuid NOT NULL REFERENCES auth.users(id),
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(campaign_id,version)
);
CREATE FUNCTION instagram_link.immutable_campaign_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Campaign versions are immutable'; END $$;
CREATE TRIGGER campaign_versions_immutable BEFORE UPDATE OR DELETE ON instagram_link.campaign_versions
 FOR EACH ROW EXECUTE FUNCTION instagram_link.immutable_campaign_version();
CREATE TABLE instagram_link.pilot_reviews (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), organization_id uuid NOT NULL, campaign_id uuid NOT NULL,
 campaign_version integer NOT NULL, encrypted_review bytea NOT NULL, reviewed_by uuid NOT NULL REFERENCES auth.users(id),
 created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL DEFAULT now()+interval '15 minutes',
 FOREIGN KEY(campaign_id,organization_id) REFERENCES instagram_link.campaigns(id,organization_id),
 FOREIGN KEY(campaign_id,campaign_version) REFERENCES instagram_link.campaign_versions(campaign_id,version)
);
CREATE TABLE instagram_link.catalog_audit (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), organization_id uuid NOT NULL REFERENCES instagram_link.organizations(id),
 actor_id uuid NOT NULL REFERENCES auth.users(id), action text NOT NULL, target_id uuid NOT NULL,
 version integer, created_at timestamptz NOT NULL DEFAULT now()
);
DO $$ DECLARE item text; BEGIN
 FOREACH item IN ARRAY ARRAY['cockpit_sessions','products','publications','campaigns','campaign_versions','pilot_reviews','catalog_audit'] LOOP
  EXECUTE format('ALTER TABLE instagram_link.%I ENABLE ROW LEVEL SECURITY',item);
  EXECUTE format('REVOKE ALL ON instagram_link.%I FROM PUBLIC,anon,authenticated',item);
 END LOOP;
END $$;
