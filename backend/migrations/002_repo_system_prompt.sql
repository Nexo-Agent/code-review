-- migrate:up
ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS system_prompt TEXT NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE repo_integrations DROP COLUMN IF EXISTS system_prompt;
