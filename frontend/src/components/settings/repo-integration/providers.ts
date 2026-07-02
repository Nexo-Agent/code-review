import type { RepoIntegrationCreate } from "@/api/settings-types"

export const GITLAB_CLOUD_BASE_URL = "https://gitlab.com"

/** Value persisted in repo_integrations.git_provider */
export type StoredGitProvider =
  | "github"
  | "azure-devops"
  | "gitlab"
  | "bitbucket"
  | "bitbucket-dc"

/** Picker card id; GitLab Cloud/Self-hosted share stored provider `gitlab`. */
export type GitProviderPickerId =
  | "github"
  | "azure-devops"
  | "gitlab-cloud"
  | "gitlab-self-hosted"
  | "bitbucket"
  | "bitbucket-dc"

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
  requireBitbucketDcBaseUrl?: boolean
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
    label: "GitLab",
    description: "",
    repoLabel: "Repository (group/project)",
    repoPlaceholder: "acme-corp/backend-api",
    gitlabBaseUrlDefault: "",
  },
  {
    id: "gitlab-self-hosted",
    gitProvider: "gitlab",
    label: "GitLab DC",
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
    description: "Connect a Bitbucket Cloud repository for pull request reviews.",
    repoLabel: "Repository (workspace/repo)",
    repoPlaceholder: "acme-corp/backend-api",
  },
  {
    id: "bitbucket-dc",
    gitProvider: "bitbucket-dc",
    label: "Bitbucket DC",
    description:
      "Connect a repository on your Bitbucket Data Center instance for pull request reviews.",
    repoLabel: "Repository (projectKey/repoSlug)",
    repoPlaceholder: "ACME/backend-api",
    requireBitbucketDcBaseUrl: true,
  },
]

export const GIT_PROVIDER_OPTIONS = [
  { value: "github", label: "GitHub" },
  { value: "azure-devops", label: "Azure DevOps" },
  { value: "gitlab", label: "GitLab Cloud" },
  { value: "gitlab-self-hosted", label: "GitLab Self-hosted" },
  { value: "bitbucket", label: "Bitbucket Cloud" },
  { value: "bitbucket-dc", label: "Bitbucket Data Center" },
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

export function gitProviderDisplayLabel(
  gitProvider: string,
  gitlabBaseUrl = "",
): string {
  return (
    getGitProviderForStoredValue(gitProvider, gitlabBaseUrl)?.label ?? gitProvider
  )
}

/** Short instance hint for self-hosted or org-scoped providers. */
export function gitProviderInstanceHint(
  repo: Pick<
    RepoIntegrationCreate,
    | "git_provider"
    | "gitlab_base_url"
    | "bitbucket_dc_base_url"
    | "ado_organization"
    | "ado_project"
  > & {
    git_provider: string
    gitlab_base_url?: string
    bitbucket_dc_base_url?: string
    ado_organization?: string
    ado_project?: string
  },
): string | null {
  if (repo.git_provider === "gitlab" && !isGitLabCloudUrl(repo.gitlab_base_url ?? "")) {
    return shortenUrl(repo.gitlab_base_url ?? "")
  }
  if (repo.git_provider === "bitbucket-dc" && repo.bitbucket_dc_base_url?.trim()) {
    return shortenUrl(repo.bitbucket_dc_base_url)
  }
  if (repo.git_provider === "azure-devops") {
    const parts = [repo.ado_organization, repo.ado_project].filter(Boolean)
    return parts.length ? parts.join(" / ") : null
  }
  return null
}

function shortenUrl(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }
  try {
    return new URL(trimmed).host
  } catch {
    return trimmed.replace(/^https?:\/\//, "").replace(/\/$/, "")
  }
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
    bitbucket_token: "",
    bitbucket_webhook_secret: "",
    bitbucket_dc_base_url: "",
    bitbucket_dc_token: "",
    bitbucket_dc_webhook_username: "",
    bitbucket_dc_webhook_password: "",
    enabled: true,
  }
}
