-- migrate:up
ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS bitbucket_token TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS bitbucket_webhook_secret TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS bitbucket_dc_base_url TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS bitbucket_dc_token TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS bitbucket_dc_webhook_username TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS bitbucket_dc_webhook_password TEXT NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE repo_integrations
  DROP COLUMN IF EXISTS bitbucket_token,
  DROP COLUMN IF EXISTS bitbucket_webhook_secret,
  DROP COLUMN IF EXISTS bitbucket_dc_base_url,
  DROP COLUMN IF EXISTS bitbucket_dc_token,
  DROP COLUMN IF EXISTS bitbucket_dc_webhook_username,
  DROP COLUMN IF EXISTS bitbucket_dc_webhook_password;
