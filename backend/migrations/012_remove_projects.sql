-- migrate:up

ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE CASCADE;

UPDATE repo_integrations ri
SET team_id = p.team_id
FROM projects p
WHERE p.id = ri.project_id
  AND ri.team_id IS NULL;

ALTER TABLE repo_integrations
  ALTER COLUMN team_id SET NOT NULL;

DROP INDEX IF EXISTS repo_integrations_project_repo_full_name_idx;

CREATE UNIQUE INDEX IF NOT EXISTS repo_integrations_team_repo_full_name_idx
  ON repo_integrations (team_id, repo_full_name);

CREATE INDEX IF NOT EXISTS idx_repo_integrations_team_id
  ON repo_integrations (team_id);

ALTER TABLE repo_integrations DROP COLUMN IF EXISTS project_id;

DROP INDEX IF EXISTS idx_reviews_project_id;

ALTER TABLE reviews DROP COLUMN IF EXISTS project_id;

DROP TABLE IF EXISTS projects;

-- migrate:down

CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  llm_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_team_id ON projects (team_id);

INSERT INTO projects (id, team_id, name, description)
SELECT
  gen_random_uuid(),
  t.id,
  'Default Project',
  'Restored default project'
FROM teams t
ON CONFLICT DO NOTHING;

ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;

UPDATE repo_integrations ri
SET project_id = (
  SELECT p.id FROM projects p WHERE p.team_id = ri.team_id LIMIT 1
)
WHERE project_id IS NULL;

ALTER TABLE repo_integrations
  ALTER COLUMN project_id SET NOT NULL;

DROP INDEX IF EXISTS repo_integrations_team_repo_full_name_idx;
DROP INDEX IF EXISTS idx_repo_integrations_team_id;

CREATE UNIQUE INDEX IF NOT EXISTS repo_integrations_project_repo_full_name_idx
  ON repo_integrations (project_id, repo_full_name);

ALTER TABLE repo_integrations DROP COLUMN IF EXISTS team_id;

ALTER TABLE reviews
  ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;

UPDATE reviews r
SET project_id = ri.project_id
FROM repo_integrations ri
WHERE r.repo_integration_id = ri.id
  AND r.project_id IS NULL;

ALTER TABLE reviews
  ALTER COLUMN project_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_reviews_project_id ON reviews (project_id);
