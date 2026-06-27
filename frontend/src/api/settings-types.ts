export interface LlmProvider {
  id: string
  name: string
  provider_id: string
  base_url: string
  model: string
  opencode_model: string
  resolved_opencode_model: string
  is_default: boolean
  enabled: boolean
  api_token_configured: boolean
  created_at: string
  updated_at: string
}

export interface LlmProviderCreate {
  name: string
  provider_id: string
  base_url: string
  api_token?: string
  model: string
  opencode_model?: string
  is_default?: boolean
  enabled?: boolean
}

export interface LlmProviderUpdate {
  name?: string
  provider_id?: string
  base_url?: string
  api_token?: string
  model?: string
  opencode_model?: string
  is_default?: boolean
  enabled?: boolean
}

export interface RepoIntegration {
  id: string
  project_id: string
  name: string
  git_provider: string
  repo_full_name: string
  llm_provider_id: string | null
  llm_provider_name: string | null
  system_prompt: string
  enabled: boolean
  github_webhook_secret_configured: boolean
  github_token_configured: boolean
  ado_organization: string
  ado_project: string
  ado_pat_configured: boolean
  ado_webhook_configured: boolean
  webhook_url: string
  created_at: string
  updated_at: string
}

export interface RepoIntegrationCreate {
  name?: string
  git_provider?: string
  repo_full_name?: string
  github_webhook_secret?: string
  github_token?: string
  ado_organization?: string
  ado_project?: string
  ado_pat?: string
  ado_webhook_username?: string
  ado_webhook_password?: string
  system_prompt?: string
  llm_provider_id?: string | null
  enabled?: boolean
}

export interface RepoIntegrationUpdate {
  name?: string
  git_provider?: string
  repo_full_name?: string
  github_webhook_secret?: string
  github_token?: string
  ado_organization?: string
  ado_project?: string
  ado_pat?: string
  ado_webhook_username?: string
  ado_webhook_password?: string
  system_prompt?: string
  llm_provider_id?: string | null
  clear_llm_provider_id?: boolean
  enabled?: boolean
}
