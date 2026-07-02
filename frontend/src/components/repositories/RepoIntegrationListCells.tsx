import { Link } from "@tanstack/react-router"

import type { RepoIntegration } from "@/api/settings-types"
import { ProviderLogo } from "@/components/settings/repo-integration/ProviderLogo"
import {
  gitProviderDisplayLabel,
  gitProviderInstanceHint,
  gitProviderLogoId,
} from "@/components/settings/repo-integration/providers"
import { Switch } from "@/components/ui/switch"
import { cn } from "@/lib/utils"

type RepoRow = Pick<
  RepoIntegration,
  | "id"
  | "team_id"
  | "name"
  | "git_provider"
  | "repo_full_name"
  | "gitlab_base_url"
  | "bitbucket_dc_base_url"
  | "ado_organization"
  | "ado_project"
  | "llm_provider_name"
  | "enabled"
>

export function RepoIntegrationNameCell({
  repo,
  teamId,
}: {
  repo: RepoRow
  teamId: string
}) {
  return (
    <div className="flex items-center gap-2.5">
      <ProviderLogo
        providerId={gitProviderLogoId(repo.git_provider, repo.gitlab_base_url)}
        className="size-5"
      />
      <Link
        to="/teams/$teamId/repos/$repoId"
        params={{ teamId, repoId: repo.id }}
        className="min-w-0 font-medium hover:underline"
      >
        {repo.repo_full_name || repo.name || "All repositories"}
      </Link>
    </div>
  )
}

export function RepoIntegrationProviderCell({ repo }: { repo: RepoRow }) {
  const label = gitProviderDisplayLabel(repo.git_provider, repo.gitlab_base_url)
  const hint = gitProviderInstanceHint(repo)

  return (
    <div className="min-w-0">
      <p className="text-sm font-medium">{label}</p>
      {hint ? (
        <p className="text-muted-foreground truncate text-xs">{hint}</p>
      ) : null}
    </div>
  )
}

export function RepoIntegrationLlmCell({ repo }: { repo: RepoRow }) {
  return <span>{repo.llm_provider_name ?? "Org default"}</span>
}

export function RepoIntegrationEnabledCell({ repo }: { repo: RepoRow }) {
  return (
    <div className="flex items-center justify-end gap-2">
      <span
        className={cn(
          "text-xs font-medium",
          repo.enabled ? "text-emerald-600" : "text-muted-foreground",
        )}
      >
        {repo.enabled ? "Enabled" : "Disabled"}
      </span>
      <Switch checked={repo.enabled} disabled aria-label="Repository enabled" />
    </div>
  )
}
