-- migrate:up
ALTER TABLE llm_providers
  ALTER COLUMN model SET DEFAULT '';

ALTER TABLE integration_settings
  ALTER COLUMN llm_provider_id SET DEFAULT '',
  ALTER COLUMN llm_base_url SET DEFAULT '',
  ALTER COLUMN llm_model SET DEFAULT '',
  ALTER COLUMN opencode_model SET DEFAULT '';

UPDATE integration_settings
SET
  llm_provider_id = '',
  llm_base_url = '',
  llm_model = '',
  opencode_model = ''
WHERE id = 1;

-- migrate:down
ALTER TABLE llm_providers
  ALTER COLUMN model SET DEFAULT 'gpt-4o';

ALTER TABLE integration_settings
  ALTER COLUMN llm_provider_id SET DEFAULT 'openai-compat',
  ALTER COLUMN llm_base_url SET DEFAULT 'https://api.openai.com/v1',
  ALTER COLUMN llm_model SET DEFAULT 'gpt-4o',
  ALTER COLUMN opencode_model SET DEFAULT '';

UPDATE integration_settings
SET
  llm_provider_id = 'openai-compat',
  llm_base_url = 'https://api.openai.com/v1',
  llm_model = 'gpt-4o',
  opencode_model = ''
WHERE id = 1;
