-- migrate:up
ALTER TABLE repo_integrations
  ADD COLUMN IF NOT EXISTS llm_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL;

UPDATE repo_integrations ri
SET llm_provider_id = p.llm_provider_id
FROM projects p
WHERE p.id = ri.project_id
  AND ri.llm_provider_id IS NULL
  AND p.llm_provider_id IS NOT NULL;

-- migrate:down
ALTER TABLE repo_integrations DROP COLUMN IF EXISTS llm_provider_id;
