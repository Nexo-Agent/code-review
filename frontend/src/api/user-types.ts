export interface UserListItem {
  id: string
  email: string
  name: string
  username: string | null
  auth_source: string
  is_org_admin: boolean
  is_superuser: boolean
  team_names: string
  created_at: string
}

export interface UserList {
  items: UserListItem[]
  total: number
}
