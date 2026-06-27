-- migrate:up

CREATE TABLE IF NOT EXISTS system_install (
  singleton BOOLEAN PRIMARY KEY DEFAULT true CHECK (singleton),
  completed_at TIMESTAMPTZ
);

INSERT INTO system_install (singleton, completed_at)
VALUES (
  true,
  CASE WHEN EXISTS (SELECT 1 FROM users LIMIT 1) THEN now() ELSE NULL END
)
ON CONFLICT (singleton) DO NOTHING;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS auth_source TEXT NOT NULL DEFAULT 'sso';

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS username TEXT;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS password_hash TEXT;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT false;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'users_auth_source_check'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT users_auth_source_check
      CHECK (auth_source IN ('sso', 'local'));
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS users_username_idx
  ON users (username)
  WHERE username IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS users_one_local_superuser_idx
  ON users (is_superuser)
  WHERE is_superuser = true AND auth_source = 'local';

-- migrate:down

DROP INDEX IF EXISTS users_one_local_superuser_idx;
DROP INDEX IF EXISTS users_username_idx;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_auth_source_check;

ALTER TABLE users DROP COLUMN IF EXISTS is_superuser;
ALTER TABLE users DROP COLUMN IF EXISTS password_hash;
ALTER TABLE users DROP COLUMN IF EXISTS username;
ALTER TABLE users DROP COLUMN IF EXISTS auth_source;

DROP TABLE IF EXISTS system_install;
