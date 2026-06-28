import type { LlmProviderCreate, RepoIntegrationCreate } from "@/api/settings-types"

export {
  llmProviderIdOptions,
} from "@/components/settings/llm-provider/providers"

export { GIT_PROVIDER_OPTIONS } from "@/components/settings/repo-integration/providers"

export function emptyLlmForm(): LlmProviderCreate {
  return {
    name: "",
    provider_id: "openai-compat",
    base_url: "https://api.openai.com/v1",
    model: "",
    api_token: "",
    is_default: false,
    enabled: true,
  }
}

export function emptyRepoForm(): RepoIntegrationCreate {
  return {
    name: "",
    git_provider: "github",
    repo_full_name: "",
    github_webhook_secret: "",
    github_token: "",
    ado_pat: "",
    ado_webhook_username: "",
    ado_webhook_password: "",
    gitlab_base_url: "",
    gitlab_token: "",
    gitlab_webhook_secret: "",
    bitbucket_token: "",
    bitbucket_webhook_secret: "",
    bitbucket_dc_base_url: "",
    bitbucket_dc_token: "",
    bitbucket_dc_webhook_username: "",
    bitbucket_dc_webhook_password: "",
    enabled: true,
  }
}
