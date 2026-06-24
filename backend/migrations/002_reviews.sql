-- migrate:up
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

-- migrate:down
DROP TABLE IF EXISTS review_findings;
DROP TABLE IF EXISTS reviews;
