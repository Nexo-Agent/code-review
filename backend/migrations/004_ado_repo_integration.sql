-- migrate:up
ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS ado_organization TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS ado_project TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS ado_pat TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS ado_webhook_username TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS ado_webhook_password TEXT NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE repo_integrations
  DROP COLUMN IF EXISTS ado_organization,
  DROP COLUMN IF EXISTS ado_project,
  DROP COLUMN IF EXISTS ado_pat,
  DROP COLUMN IF EXISTS ado_webhook_username,
  DROP COLUMN IF EXISTS ado_webhook_password;
