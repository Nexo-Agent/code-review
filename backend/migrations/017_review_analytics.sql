-- migrate:up
CREATE TABLE IF NOT EXISTS review_comment_artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  review_finding_id UUID REFERENCES review_findings(id) ON DELETE SET NULL,
  provider TEXT NOT NULL,
  repo_full_name TEXT NOT NULL,
  pr_number INT NOT NULL,
  comment_kind TEXT NOT NULL,
  remote_comment_id TEXT NOT NULL,
  remote_thread_id TEXT,
  file_path TEXT,
  line_start INT,
  side TEXT NOT NULL DEFAULT 'RIGHT',
  posted_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_review_comment_artifacts_remote
  ON review_comment_artifacts (provider, repo_full_name, pr_number, remote_comment_id);

CREATE INDEX IF NOT EXISTS idx_review_comment_artifacts_review_id
  ON review_comment_artifacts (review_id);

CREATE TABLE IF NOT EXISTS review_engagement_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  repo_full_name TEXT NOT NULL,
  pr_number INT NOT NULL,
  review_id UUID REFERENCES reviews(id) ON DELETE SET NULL,
  review_finding_id UUID REFERENCES review_findings(id) ON DELETE SET NULL,
  comment_artifact_id UUID REFERENCES review_comment_artifacts(id) ON DELETE SET NULL,
  repo_integration_id UUID REFERENCES repo_integrations(id) ON DELETE SET NULL,
  team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
  event_family TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_at TIMESTAMPTZ NOT NULL,
  actor_login TEXT NOT NULL DEFAULT '',
  actor_type TEXT NOT NULL DEFAULT 'unknown',
  provider_delivery_id TEXT NOT NULL DEFAULT '',
  provider_event_id TEXT NOT NULL DEFAULT '',
  provider_object_id TEXT NOT NULL DEFAULT '',
  dedup_key TEXT NOT NULL UNIQUE,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  normalized_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_review_engagement_events_repo_pr
  ON review_engagement_events (provider, repo_full_name, pr_number, event_at);

CREATE INDEX IF NOT EXISTS idx_review_engagement_events_review_id
  ON review_engagement_events (review_id);

CREATE TABLE IF NOT EXISTS review_metrics_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_key TEXT NOT NULL,
  provider TEXT NOT NULL,
  granularity TEXT NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  dimension_key TEXT NOT NULL,
  repo_integration_id UUID REFERENCES repo_integrations(id) ON DELETE SET NULL,
  team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
  repo_full_name TEXT NOT NULL DEFAULT '',
  metric_value_num DOUBLE PRECISION NOT NULL DEFAULT 0,
  numerator DOUBLE PRECISION,
  denominator DOUBLE PRECISION,
  sample_size INT NOT NULL DEFAULT 0,
  dimensions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  job_run_id UUID NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_review_metrics_analytics_unique
  ON review_metrics_analytics (
    metric_key, provider, granularity, window_start, window_end, dimension_key
  );

CREATE INDEX IF NOT EXISTS idx_review_metrics_analytics_window
  ON review_metrics_analytics (window_end DESC, metric_key);

-- migrate:down
DROP TABLE IF EXISTS review_metrics_analytics;
DROP TABLE IF EXISTS review_engagement_events;
DROP TABLE IF EXISTS review_comment_artifacts;
