-- migrate:up
CREATE TABLE IF NOT EXISTS llm_token_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
  repo_integration_id UUID REFERENCES repo_integrations(id) ON DELETE SET NULL,
  llm_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL,
  git_provider TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  call_index INT NOT NULL,
  input_tokens INT NOT NULL DEFAULT 0,
  output_tokens INT NOT NULL DEFAULT 0,
  total_tokens INT NOT NULL DEFAULT 0,
  reason TEXT NOT NULL DEFAULT '',
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_token_usage_review_call
  ON llm_token_usage (review_id, call_index);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_occurred_at
  ON llm_token_usage (occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_team_occurred_at
  ON llm_token_usage (team_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_repo_occurred_at
  ON llm_token_usage (repo_integration_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_llm_provider_occurred_at
  ON llm_token_usage (llm_provider_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_git_provider_occurred_at
  ON llm_token_usage (git_provider, occurred_at DESC);

CREATE TABLE IF NOT EXISTS usage_metrics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_key TEXT NOT NULL,
  granularity TEXT NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  dimension_key TEXT NOT NULL,
  team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
  repo_integration_id UUID REFERENCES repo_integrations(id) ON DELETE SET NULL,
  llm_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL,
  git_provider TEXT NOT NULL DEFAULT '',
  metric_value_num DOUBLE PRECISION NOT NULL DEFAULT 0,
  sample_size INT NOT NULL DEFAULT 0,
  job_run_id UUID NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_metrics_daily_unique
  ON usage_metrics_daily (
    metric_key, granularity, window_start, dimension_key
  );

CREATE INDEX IF NOT EXISTS idx_usage_metrics_daily_window
  ON usage_metrics_daily (window_end DESC, metric_key);

-- migrate:down
DROP TABLE IF EXISTS usage_metrics_daily;
DROP TABLE IF EXISTS llm_token_usage;
