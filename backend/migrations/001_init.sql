-- migrate:up
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS examples (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_examples_created_at ON examples (created_at DESC);

CREATE TABLE IF NOT EXISTS reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL DEFAULT 'github',
  repo_full_name TEXT NOT NULL,
  pr_number INT NOT NULL,
  head_sha TEXT NOT NULL,
  status TEXT NOT NULL,
  delivery_id TEXT UNIQUE,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS review_findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  severity TEXT NOT NULL,
  file_path TEXT,
  line_start INT,
  line_end INT,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_repo_pr_sha
  ON reviews (repo_full_name, pr_number, head_sha);

CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews (status);
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_findings_review_id ON review_findings (review_id);

CREATE TABLE IF NOT EXISTS integration_settings (
  id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  git_provider TEXT NOT NULL DEFAULT 'github',
  github_repo_full_name TEXT NOT NULL DEFAULT '',
  github_webhook_secret TEXT NOT NULL DEFAULT '',
  github_token TEXT NOT NULL DEFAULT '',
  llm_provider_id TEXT NOT NULL DEFAULT '',
  llm_base_url TEXT NOT NULL DEFAULT '',
  llm_api_token TEXT NOT NULL DEFAULT '',
  llm_model TEXT NOT NULL DEFAULT '',
  opencode_model TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO integration_settings (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS llm_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  provider_id TEXT NOT NULL,
  base_url TEXT NOT NULL DEFAULT 'https://api.openai.com/v1',
  api_token TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  opencode_model TEXT NOT NULL DEFAULT '',
  is_default BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS llm_providers_name_idx ON llm_providers (name);
CREATE UNIQUE INDEX IF NOT EXISTS llm_providers_provider_id_idx ON llm_providers (provider_id);
CREATE UNIQUE INDEX IF NOT EXISTS llm_providers_one_default_idx
  ON llm_providers (is_default) WHERE is_default = true;

CREATE TABLE IF NOT EXISTS repo_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL DEFAULT '',
  git_provider TEXT NOT NULL DEFAULT 'github',
  repo_full_name TEXT NOT NULL DEFAULT '',
  github_webhook_secret TEXT NOT NULL DEFAULT '',
  github_token TEXT NOT NULL DEFAULT '',
  llm_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL,
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS repo_integrations_repo_full_name_idx
  ON repo_integrations (repo_full_name);

ALTER TABLE reviews
  ADD COLUMN IF NOT EXISTS repo_integration_id UUID
  REFERENCES repo_integrations(id) ON DELETE SET NULL;

-- migrate:down
ALTER TABLE reviews DROP COLUMN IF EXISTS repo_integration_id;
DROP TABLE IF EXISTS repo_integrations;
DROP TABLE IF EXISTS llm_providers;
DROP TABLE IF EXISTS integration_settings;
DROP TABLE IF EXISTS review_findings;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS examples;
