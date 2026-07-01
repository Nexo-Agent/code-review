export interface User {
  id: string
  email: string
  name: string
  is_org_admin: boolean
  created_at: string
}

export interface TeamMembership {
  team_id: string
  role_key: string
}

export interface PermissionsSummary {
  organization: string[]
  teams: Record<string, string[]>
}

export interface MeResponse {
  user: User
  team_ids: string[]
  auth_enabled: boolean
  organization_roles: string[]
  team_memberships: TeamMembership[]
  permissions: PermissionsSummary | null
}

export type ActionKey =
  | "team.create"
  | "team.read"
  | "team.update"
  | "team.delete"
  | "team.member.read"
  | "team.member.add"
  | "team.member.update_role"
  | "team.member.remove"
  | "repo.read"
  | "repo.create"
  | "repo.update"
  | "repo.delete"
  | "repo.configure_credentials"
  | "review.read"
  | "review.rerun"
  | "review.finding.read"
  | "user.read"
  | "user.assign_org_admin"
  | "user.deactivate"
  | "settings.sso.read"
  | "settings.sso.update"
  | "settings.llm.read"
  | "settings.llm.update"
  | "settings.rbac.read"
  | "settings.rbac.update"
  | "settings.usage.read"
