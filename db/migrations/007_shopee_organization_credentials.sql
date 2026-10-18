CREATE TABLE instagram_link.shopee_organization_credentials (
 organization_id uuid PRIMARY KEY REFERENCES instagram_link.organizations(id),
 encrypted_credentials bytea NOT NULL,
 configured_by uuid NOT NULL REFERENCES auth.users(id),
 configured_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE instagram_link.shopee_organization_credentials ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON instagram_link.shopee_organization_credentials FROM PUBLIC,anon,authenticated;
