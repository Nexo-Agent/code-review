import type { LlmProviderCreate, RepoIntegrationCreate } from "@/api/settings-types"

export const GIT_PROVIDER_OPTIONS = [
  { value: "github", label: "GitHub" },
  { value: "azure-devops", label: "Azure DevOps" },
  { value: "gitlab", label: "GitLab (coming soon)", disabled: true },
] as const

export const LLM_PROVIDER_ID_OPTIONS = [
  { value: "openai-compat", label: "OpenAI Compatible API" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "groq", label: "Groq" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "ollama", label: "Ollama (local)" },
] as const

export function llmProviderIdOptions(current?: string) {
  const options = [...LLM_PROVIDER_ID_OPTIONS]
  if (
    current &&
    !options.some((option) => option.value === current)
  ) {
    return [{ value: current, label: current }, ...options]
  }
  return options
}

export function emptyLlmForm(): LlmProviderCreate {
  return {
    name: "",
    provider_id: "openai-compat",
    base_url: "https://api.openai.com/v1",
    model: "gpt-4o",
    api_token: "",
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
    ado_organization: "",
    ado_project: "",
    ado_pat: "",
    ado_webhook_username: "",
    ado_webhook_password: "",
    llm_provider_id: null,
    enabled: true,
  }
}
