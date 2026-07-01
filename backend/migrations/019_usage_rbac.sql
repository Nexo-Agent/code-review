-- migrate:up
INSERT INTO rbac_actions (key, display_name) VALUES
  ('settings.usage.read', 'Read Usage Statistics')
ON CONFLICT (key) DO NOTHING;

INSERT INTO rbac_role_permissions (role_id, action_id, resource_scope_id, allowed)
SELECT r.id, a.id, s.id, true
FROM rbac_roles r
CROSS JOIN rbac_actions a
CROSS JOIN rbac_resource_scopes s
WHERE r.key = 'org_admin'
  AND a.key = 'settings.usage.read'
ON CONFLICT (role_id, action_id, resource_scope_id) DO NOTHING;

-- migrate:down
DELETE FROM rbac_role_permissions
WHERE action_id IN (
  SELECT id FROM rbac_actions WHERE key = 'settings.usage.read'
);

DELETE FROM rbac_actions WHERE key = 'settings.usage.read';
