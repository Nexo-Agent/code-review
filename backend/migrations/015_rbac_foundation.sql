-- migrate:up

CREATE TABLE IF NOT EXISTS rbac_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  scope_kind TEXT NOT NULL CHECK (scope_kind IN ('organization', 'team', 'system')),
  description TEXT NOT NULL DEFAULT '',
  is_system BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rbac_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rbac_resource_scopes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rbac_role_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_id UUID NOT NULL REFERENCES rbac_roles(id) ON DELETE CASCADE,
  action_id UUID NOT NULL REFERENCES rbac_actions(id) ON DELETE CASCADE,
  resource_scope_id UUID NOT NULL REFERENCES rbac_resource_scopes(id) ON DELETE CASCADE,
  allowed BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (role_id, action_id, resource_scope_id)
);

CREATE TABLE IF NOT EXISTS organization_user_roles (
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES rbac_roles(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_organization_user_roles_user_id
  ON organization_user_roles (user_id);

-- Seed resource scopes
INSERT INTO rbac_resource_scopes (key, display_name) VALUES
  ('organization', 'Organization'),
  ('team', 'Team'),
  ('repository', 'Repository'),
  ('review', 'Review'),
  ('user', 'User'),
  ('settings', 'Settings')
ON CONFLICT (key) DO NOTHING;

-- Seed roles
INSERT INTO rbac_roles (key, display_name, scope_kind, description, is_system) VALUES
  ('org_admin', 'Organization Admin', 'organization', 'Full administrative authority across the organization', false),
  ('org_member', 'Organization Member', 'organization', 'Base organization role with no special admin permissions', false),
  ('team_admin', 'Team Admin', 'team', 'Administrative authority within a team', false),
  ('member', 'Member', 'team', 'Operational contributor within a team', false),
  ('viewer', 'Viewer', 'team', 'Read-only access within a team', false)
ON CONFLICT (key) DO NOTHING;

-- Seed actions
INSERT INTO rbac_actions (key, display_name) VALUES
  ('team.create', 'Create Team'),
  ('team.read', 'Read Team'),
  ('team.update', 'Update Team'),
  ('team.delete', 'Delete Team'),
  ('team.member.read', 'Read Team Members'),
  ('team.member.add', 'Add Team Member'),
  ('team.member.update_role', 'Update Team Member Role'),
  ('team.member.remove', 'Remove Team Member'),
  ('repo.read', 'Read Repository'),
  ('repo.create', 'Create Repository'),
  ('repo.update', 'Update Repository'),
  ('repo.delete', 'Delete Repository'),
  ('repo.configure_credentials', 'Configure Repository Credentials'),
  ('review.read', 'Read Review'),
  ('review.rerun', 'Rerun Review'),
  ('review.finding.read', 'Read Review Findings'),
  ('user.read', 'Read Users'),
  ('user.assign_org_admin', 'Assign Organization Admin'),
  ('user.deactivate', 'Deactivate User'),
  ('settings.sso.read', 'Read SSO Settings'),
  ('settings.sso.update', 'Update SSO Settings'),
  ('settings.llm.read', 'Read LLM Settings'),
  ('settings.llm.update', 'Update LLM Settings'),
  ('settings.rbac.read', 'Read RBAC Settings'),
  ('settings.rbac.update', 'Update RBAC Settings')
ON CONFLICT (key) DO NOTHING;

-- org_admin: all actions on all scopes
INSERT INTO rbac_role_permissions (role_id, action_id, resource_scope_id, allowed)
SELECT r.id, a.id, s.id, true
FROM rbac_roles r
CROSS JOIN rbac_actions a
CROSS JOIN rbac_resource_scopes s
WHERE r.key = 'org_admin'
ON CONFLICT (role_id, action_id, resource_scope_id) DO NOTHING;

-- team_admin: team-scoped administrative and operational actions
INSERT INTO rbac_role_permissions (role_id, action_id, resource_scope_id, allowed)
SELECT r.id, a.id, s.id, true
FROM rbac_roles r
CROSS JOIN rbac_actions a
CROSS JOIN rbac_resource_scopes s
WHERE r.key = 'team_admin'
  AND s.key = 'team'
  AND a.key IN (
    'team.read', 'team.update',
    'team.member.read', 'team.member.add', 'team.member.update_role', 'team.member.remove',
    'repo.read', 'repo.create', 'repo.update', 'repo.delete', 'repo.configure_credentials',
    'review.read', 'review.rerun', 'review.finding.read'
  )
ON CONFLICT (role_id, action_id, resource_scope_id) DO NOTHING;

-- member: read + operational review actions at team scope
INSERT INTO rbac_role_permissions (role_id, action_id, resource_scope_id, allowed)
SELECT r.id, a.id, s.id, true
FROM rbac_roles r
CROSS JOIN rbac_actions a
CROSS JOIN rbac_resource_scopes s
WHERE r.key = 'member'
  AND s.key = 'team'
  AND a.key IN (
    'team.read',
    'repo.read',
    'review.read', 'review.rerun', 'review.finding.read'
  )
ON CONFLICT (role_id, action_id, resource_scope_id) DO NOTHING;

-- viewer: read-only at team scope
INSERT INTO rbac_role_permissions (role_id, action_id, resource_scope_id, allowed)
SELECT r.id, a.id, s.id, true
FROM rbac_roles r
CROSS JOIN rbac_actions a
CROSS JOIN rbac_resource_scopes s
WHERE r.key = 'viewer'
  AND s.key = 'team'
  AND a.key IN (
    'team.read',
    'repo.read',
    'review.read', 'review.finding.read'
  )
ON CONFLICT (role_id, action_id, resource_scope_id) DO NOTHING;

-- org_member: org-level team.read and settings.llm.read
INSERT INTO rbac_role_permissions (role_id, action_id, resource_scope_id, allowed)
SELECT r.id, a.id, s.id, true
FROM rbac_roles r
CROSS JOIN rbac_actions a
CROSS JOIN rbac_resource_scopes s
WHERE r.key = 'org_member'
  AND (
    (s.key = 'organization' AND a.key = 'team.read')
    OR (s.key = 'settings' AND a.key = 'settings.llm.read')
  )
ON CONFLICT (role_id, action_id, resource_scope_id) DO NOTHING;

-- Normalize team_members.role -> role_id
ALTER TABLE team_members
  ADD COLUMN IF NOT EXISTS role_id UUID REFERENCES rbac_roles(id) ON DELETE RESTRICT;

UPDATE team_members tm
SET role_id = r.id
FROM rbac_roles r
WHERE tm.role_id IS NULL
  AND r.key = CASE
    WHEN tm.role = 'team_admin' THEN 'team_admin'
    WHEN tm.role = 'viewer' THEN 'viewer'
    ELSE 'member'
  END;

UPDATE team_members tm
SET role_id = (SELECT id FROM rbac_roles WHERE key = 'member')
WHERE tm.role_id IS NULL;

ALTER TABLE team_members
  ALTER COLUMN role_id SET NOT NULL;

ALTER TABLE team_members DROP COLUMN IF EXISTS role;

-- Backfill organization role assignments
INSERT INTO organization_user_roles (organization_id, user_id, role_id)
SELECT
  '00000000-0000-4000-8000-000000000001',
  u.id,
  r.id
FROM users u
JOIN rbac_roles r ON r.key = CASE
  WHEN u.is_org_admin = true OR u.is_superuser = true THEN 'org_admin'
  ELSE 'org_member'
END
ON CONFLICT DO NOTHING;

-- migrate:down

ALTER TABLE team_members
  ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'member';

UPDATE team_members tm
SET role = r.key
FROM rbac_roles r
WHERE tm.role_id = r.id;

ALTER TABLE team_members DROP COLUMN IF EXISTS role_id;

DROP TABLE IF EXISTS organization_user_roles;
DROP TABLE IF EXISTS rbac_role_permissions;
DROP TABLE IF EXISTS rbac_actions;
DROP TABLE IF EXISTS rbac_resource_scopes;
DROP TABLE IF EXISTS rbac_roles;
