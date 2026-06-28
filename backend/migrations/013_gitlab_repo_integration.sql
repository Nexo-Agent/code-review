-- migrate:up
ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS gitlab_base_url TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS gitlab_token TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS gitlab_webhook_secret TEXT NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE repo_integrations
  DROP COLUMN IF EXISTS gitlab_base_url,
  DROP COLUMN IF EXISTS gitlab_token,
  DROP COLUMN IF EXISTS gitlab_webhook_secret;
