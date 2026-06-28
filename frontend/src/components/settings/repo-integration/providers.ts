import type { RepoIntegrationCreate } from "@/api/settings-types"

export const GITLAB_CLOUD_BASE_URL = "https://gitlab.com"

/** Value persisted in repo_integrations.git_provider */
export type StoredGitProvider =
  | "github"
  | "azure-devops"
  | "gitlab"
  | "bitbucket"

/** Picker card id; GitLab Cloud/Self-hosted share stored provider `gitlab`. */
export type GitProviderPickerId =
  | "github"
  | "azure-devops"
  | "gitlab-cloud"
  | "gitlab-self-hosted"
  | "bitbucket"

export interface GitProviderDefinition {
  id: GitProviderPickerId
  gitProvider: StoredGitProvider
  label: string
  description: string
  repoLabel: string
  repoPlaceholder: string
  disabled?: boolean
  /** Pre-filled gitlab_base_url on create; empty means SaaS default at runtime. */
  gitlabBaseUrlDefault?: string
  requireGitlabBaseUrl?: boolean
}

export const GIT_PROVIDERS: GitProviderDefinition[] = [
  {
    id: "github",
    gitProvider: "github",
    label: "GitHub",
    description: "Connect a GitHub repository for pull request reviews.",
    repoLabel: "Repository (owner/repo)",
    repoPlaceholder: "acme-corp/backend-api",
  },
  {
    id: "azure-devops",
    gitProvider: "azure-devops",
    label: "Azure DevOps",
    description: "Connect an Azure DevOps repository for pull request reviews.",
    repoLabel: "Repository (org/project/repo)",
    repoPlaceholder: "contoso/engineering/web-app",
  },
  {
    id: "gitlab-cloud",
    gitProvider: "gitlab",
    label: "GitLab Cloud",
    description: "",
    repoLabel: "Repository (group/project)",
    repoPlaceholder: "acme-corp/backend-api",
    gitlabBaseUrlDefault: "",
  },
  {
    id: "gitlab-self-hosted",
    gitProvider: "gitlab",
    label: "GitLab",
    description:
      "Connect a repository on your own GitLab instance for merge request reviews.",
    repoLabel: "Repository (group/project)",
    repoPlaceholder: "acme-corp/backend-api",
    requireGitlabBaseUrl: true,
  },
  {
    id: "bitbucket",
    gitProvider: "bitbucket",
    label: "Bitbucket",
    description: "Bitbucket integration is coming soon.",
    repoLabel: "Repository (workspace/repo)",
    repoPlaceholder: "acme-corp/backend-api",
    disabled: true,
  },
]

export const GIT_PROVIDER_OPTIONS = [
  { value: "github", label: "GitHub" },
  { value: "azure-devops", label: "Azure DevOps" },
  { value: "gitlab", label: "GitLab Cloud" },
  { value: "gitlab-self-hosted", label: "GitLab Self-hosted" },
  { value: "bitbucket", label: "Bitbucket (coming soon)", disabled: true },
] as const

export function isGitLabCloudUrl(baseUrl: string): boolean {
  const trimmed = baseUrl.trim().replace(/\/$/, "")
  return !trimmed || trimmed === GITLAB_CLOUD_BASE_URL
}

export function getGitProvider(
  id: GitProviderPickerId,
): GitProviderDefinition | undefined {
  return GIT_PROVIDERS.find((provider) => provider.id === id)
}

export function getGitProviderForStoredValue(
  gitProvider: string,
  gitlabBaseUrl = "",
): GitProviderDefinition | undefined {
  if (gitProvider === "gitlab") {
    return isGitLabCloudUrl(gitlabBaseUrl)
      ? getGitProvider("gitlab-cloud")
      : getGitProvider("gitlab-self-hosted")
  }
  return GIT_PROVIDERS.find((provider) => provider.gitProvider === gitProvider)
}

/** @deprecated Use getGitProviderForStoredValue for API values. */
export function getGitProviderForValue(
  value: string,
  gitlabBaseUrl = "",
): GitProviderDefinition | undefined {
  return getGitProviderForStoredValue(value, gitlabBaseUrl)
}

export function isGitProviderPickerId(
  value: string,
): value is GitProviderPickerId {
  return GIT_PROVIDERS.some((provider) => provider.id === value)
}

/** Maps stored git_provider (+ GitLab base URL) to a logo/picker id. */
export function gitProviderLogoId(
  gitProvider: string,
  gitlabBaseUrl = "",
): GitProviderPickerId | StoredGitProvider {
  if (gitProvider === "gitlab") {
    return isGitLabCloudUrl(gitlabBaseUrl)
      ? "gitlab-cloud"
      : "gitlab-self-hosted"
  }
  if (isGitProviderPickerId(gitProvider)) {
    return gitProvider
  }
  return gitProvider as StoredGitProvider
}

export function repoFormFromGitProvider(
  provider: GitProviderDefinition,
): RepoIntegrationCreate {
  return {
    name: "",
    git_provider: provider.gitProvider,
    repo_full_name: "",
    github_webhook_secret: "",
    github_token: "",
    ado_pat: "",
    ado_webhook_username: "",
    ado_webhook_password: "",
    gitlab_base_url: provider.gitlabBaseUrlDefault ?? "",
    gitlab_token: "",
    gitlab_webhook_secret: "",
    enabled: true,
  }
}
