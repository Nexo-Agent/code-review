import type { RepoIntegrationCreate } from "@/api/settings-types"

export type GitProviderId = "github" | "azure-devops" | "gitlab" | "bitbucket"

export interface GitProviderDefinition {
  id: GitProviderId
  label: string
  description: string
  repoLabel: string
  repoPlaceholder: string
  disabled?: boolean
}

export const GIT_PROVIDERS: GitProviderDefinition[] = [
  {
    id: "github",
    label: "GitHub",
    description: "Connect a GitHub repository for pull request reviews.",
    repoLabel: "Repository (owner/repo)",
    repoPlaceholder: "acme-corp/backend-api",
  },
  {
    id: "azure-devops",
    label: "Azure DevOps",
    description: "Connect an Azure DevOps repository for pull request reviews.",
    repoLabel: "Repository (org/project/repo)",
    repoPlaceholder: "contoso/engineering/web-app",
  },
  {
    id: "gitlab",
    label: "GitLab",
    description: "GitLab integration is coming soon.",
    repoLabel: "Repository (group/project)",
    repoPlaceholder: "acme-corp/backend-api",
    disabled: true,
  },
  {
    id: "bitbucket",
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
  { value: "gitlab", label: "GitLab (coming soon)", disabled: true },
  { value: "bitbucket", label: "Bitbucket (coming soon)", disabled: true },
] as const

export function getGitProvider(id: GitProviderId): GitProviderDefinition | undefined {
  return GIT_PROVIDERS.find((provider) => provider.id === id)
}

export function getGitProviderForValue(
  value: string,
): GitProviderDefinition | undefined {
  return GIT_PROVIDERS.find((provider) => provider.id === value)
}

export function repoFormFromGitProvider(
  provider: GitProviderDefinition,
): RepoIntegrationCreate {
  return {
    name: "",
    git_provider: provider.id,
    repo_full_name: "",
    github_webhook_secret: "",
    github_token: "",
    ado_pat: "",
    ado_webhook_username: "",
    ado_webhook_password: "",
    enabled: true,
  }
}
