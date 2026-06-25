-- migrate:up
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS pr_title TEXT NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE reviews DROP COLUMN IF EXISTS pr_title;
