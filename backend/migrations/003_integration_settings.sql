-- migrate:up
CREATE TABLE IF NOT EXISTS integration_settings (
  id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  git_provider TEXT NOT NULL DEFAULT 'github',
  github_repo_full_name TEXT NOT NULL DEFAULT '',
  github_webhook_secret TEXT NOT NULL DEFAULT '',
  github_token TEXT NOT NULL DEFAULT '',
  llm_provider_id TEXT NOT NULL DEFAULT 'openai-compat',
  llm_base_url TEXT NOT NULL DEFAULT 'https://api.openai.com/v1',
  llm_api_token TEXT NOT NULL DEFAULT '',
  llm_model TEXT NOT NULL DEFAULT 'gpt-4o',
  opencode_model TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO integration_settings (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- migrate:down
DROP TABLE IF EXISTS integration_settings;
