-- migrate:up

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, slug)
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  oidc_sub TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL DEFAULT '',
  is_org_admin BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS team_members (
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members (user_id);

-- Organization singleton + default team/project for existing data
INSERT INTO organizations (id, name)
VALUES ('00000000-0000-4000-8000-000000000001', 'Default Organization')
ON CONFLICT DO NOTHING;

INSERT INTO teams (id, organization_id, name, slug)
VALUES (
  '00000000-0000-4000-8000-000000000002',
  '00000000-0000-4000-8000-000000000001',
  'Default Team',
  'default'
)
ON CONFLICT DO NOTHING;

ALTER TABLE llm_providers
  ADD COLUMN IF NOT EXISTS organization_id UUID
  REFERENCES organizations(id) ON DELETE CASCADE;

UPDATE llm_providers
SET organization_id = '00000000-0000-4000-8000-000000000001'
WHERE organization_id IS NULL;

ALTER TABLE llm_providers
  ALTER COLUMN organization_id SET NOT NULL;

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

INSERT INTO projects (id, team_id, name, description, llm_provider_id)
SELECT
  '00000000-0000-4000-8000-000000000003',
  '00000000-0000-4000-8000-000000000002',
  'Default Project',
  'Migrated default project',
  (SELECT id FROM llm_providers WHERE is_default = true LIMIT 1)
WHERE NOT EXISTS (
  SELECT 1 FROM projects WHERE id = '00000000-0000-4000-8000-000000000003'
);

ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS project_id UUID
  REFERENCES projects(id) ON DELETE CASCADE;

UPDATE repo_integrations ri
SET project_id = '00000000-0000-4000-8000-000000000003'
WHERE project_id IS NULL;

UPDATE projects p
SET llm_provider_id = sub.llm_id
FROM (
  SELECT DISTINCT ON (project_id) project_id, llm_provider_id AS llm_id
  FROM repo_integrations
  WHERE llm_provider_id IS NOT NULL
  ORDER BY project_id, llm_provider_id
) sub
WHERE p.id = sub.project_id
  AND p.llm_provider_id IS NULL;

ALTER TABLE repo_integrations
  ALTER COLUMN project_id SET NOT NULL;

DROP INDEX IF EXISTS repo_integrations_repo_full_name_idx;

CREATE UNIQUE INDEX IF NOT EXISTS repo_integrations_project_repo_full_name_idx
  ON repo_integrations (project_id, repo_full_name);

ALTER TABLE repo_integrations DROP COLUMN IF EXISTS llm_provider_id;

ALTER TABLE reviews
  ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE SET NULL;

ALTER TABLE reviews
  ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;

UPDATE reviews r
SET
  project_id = ri.project_id,
  team_id = p.team_id
FROM repo_integrations ri
JOIN projects p ON p.id = ri.project_id
WHERE r.repo_integration_id = ri.id
  AND (r.project_id IS NULL OR r.team_id IS NULL);

UPDATE reviews
SET
  project_id = '00000000-0000-4000-8000-000000000003',
  team_id = '00000000-0000-4000-8000-000000000002'
WHERE project_id IS NULL OR team_id IS NULL;

ALTER TABLE reviews
  ALTER COLUMN team_id SET NOT NULL;

ALTER TABLE reviews
  ALTER COLUMN project_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_reviews_team_id ON reviews (team_id);
CREATE INDEX IF NOT EXISTS idx_reviews_project_id ON reviews (project_id);

-- migrate:down

DROP INDEX IF EXISTS idx_reviews_project_id;
DROP INDEX IF EXISTS idx_reviews_team_id;

ALTER TABLE reviews DROP COLUMN IF EXISTS project_id;
ALTER TABLE reviews DROP COLUMN IF EXISTS team_id;

ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS llm_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL;

DROP INDEX IF EXISTS repo_integrations_project_repo_full_name_idx;

CREATE UNIQUE INDEX IF NOT EXISTS repo_integrations_repo_full_name_idx
  ON repo_integrations (repo_full_name);

ALTER TABLE repo_integrations DROP COLUMN IF EXISTS project_id;

DROP TABLE IF EXISTS projects;

ALTER TABLE llm_providers DROP COLUMN IF EXISTS organization_id;

DROP TABLE IF EXISTS team_members;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS organizations;
