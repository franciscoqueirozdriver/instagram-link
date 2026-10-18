ALTER TABLE instagram_link.instagram_accounts
    ADD COLUMN comments_subscription_status text NOT NULL DEFAULT 'pending'
        CHECK (comments_subscription_status IN ('pending','accepted','confirmed','failed')),
    ADD COLUMN comments_subscribed_at timestamptz;
