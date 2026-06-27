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

export interface Project {
  id: string
  team_id: string
  name: string
  description: string
  llm_provider_id: string | null
  llm_provider_name: string | null
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  llm_provider_id?: string | null
}

export interface ProjectUpdate {
  name?: string
  description?: string
  llm_provider_id?: string | null
  clear_llm_provider_id?: boolean
}

export interface TeamRepository extends RepoIntegration {
  project_name: string
}

export interface OrgRepository extends TeamRepository {
  team_id: string
  team_name: string
}
