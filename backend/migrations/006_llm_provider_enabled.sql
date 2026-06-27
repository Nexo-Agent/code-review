-- migrate:up
ALTER TABLE llm_providers
  ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT true;

-- migrate:down
ALTER TABLE llm_providers
  DROP COLUMN IF EXISTS enabled;
