-- Additive metadata only; preserve accounts, campaigns, versions and private/RLS scope.
ALTER TABLE instagram_link.publications
 ADD COLUMN thumbnail_url text,
 ADD COLUMN media_url text,
 ADD COLUMN media_product_type text;
ALTER TABLE instagram_link.instagram_accounts
 ADD COLUMN publications_cursor bytea,
 ADD COLUMN publications_synced_at timestamptz;
CREATE INDEX publications_account_page ON instagram_link.publications(organization_id,account_id,published_at DESC,id DESC);
