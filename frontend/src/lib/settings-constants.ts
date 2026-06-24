import type { LlmProviderCreate, RepoIntegrationCreate } from "@/api/settings-types"

export const GIT_PROVIDER_OPTIONS = [
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab (coming soon)", disabled: true },
] as const

export function emptyLlmForm(): LlmProviderCreate {
  return {
    name: "",
    provider_id: "openai-compat",
    base_url: "https://api.openai.com/v1",
    model: "gpt-4o",
    api_token: "",
    opencode_model: "",
    is_default: false,
  }
}

export function emptyRepoForm(): RepoIntegrationCreate {
  return {
    name: "",
    git_provider: "github",
    repo_full_name: "",
    github_webhook_secret: "",
    github_token: "",
    llm_provider_id: null,
    enabled: true,
  }
}
