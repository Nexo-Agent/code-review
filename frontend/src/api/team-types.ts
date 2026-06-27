import type { RepoIntegration } from "@/api/settings-types"

export interface Team {
  id: string
  organization_id: string
  name: string
  slug: string
  repo_count: number
  member_count: number
  created_at: string
}

export interface TeamCreate {
  name: string
  slug?: string | null
}

export interface TeamUpdate {
  name?: string
}

export interface TeamMember {
  team_id: string
  user_id: string
  role: string
  user_email: string
  user_name: string
  created_at: string
}

export interface TeamMemberCreate {
  user_id: string
  role?: string
}

export type TeamRepository = RepoIntegration

export interface OrgRepository extends RepoIntegration {
  team_name: string
}
