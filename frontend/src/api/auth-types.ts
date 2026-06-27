export interface User {
  id: string
  email: string
  name: string
  is_org_admin: boolean
  created_at: string
}

export interface MeResponse {
  user: User
  team_ids: string[]
  auth_enabled: boolean
}
