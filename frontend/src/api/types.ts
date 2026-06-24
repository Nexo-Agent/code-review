export interface HealthResponse {
  status: string
  db: string
  version: string
}

export interface Example {
  id: string
  name: string
  created_at: string
}

export interface ExampleCreate {
  name: string
}

export interface ReviewFinding {
  id: string
  severity: string
  file_path: string | null
  line_start: number | null
  line_end: number | null
  title: string
  body: string
  created_at: string
}

export interface Review {
  id: string
  provider: string
  repo_full_name: string
  pr_number: number
  head_sha: string
  status: string
  delivery_id: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  findings: ReviewFinding[]
}

export interface ReviewList {
  items: Review[]
  total: number
}

export interface IntegrationSettings {
  git_provider: string
  github_repo_full_name: string
  github_webhook_secret_configured: boolean
  github_token_configured: boolean
  llm_provider_id: string
  llm_base_url: string
  llm_model: string
  llm_api_token_configured: boolean
  opencode_model: string
  resolved_opencode_model: string
  updated_at: string
}

export interface IntegrationSettingsUpdate {
  git_provider?: string
  github_repo_full_name?: string
  github_webhook_secret?: string
  github_token?: string
  llm_provider_id?: string
  llm_base_url?: string
  llm_api_token?: string
  llm_model?: string
  opencode_model?: string
}
