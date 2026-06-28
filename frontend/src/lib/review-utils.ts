import type { RepoIntegration } from "@/api/settings-types"
import type { ReviewFinding } from "@/api/types"

export function formatReviewTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleString()
}

export function formatReviewTimestampCompact(
  iso: string | null | undefined,
): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function formatDuration(
  startedAt: string | null | undefined,
  completedAt: string | null | undefined,
): string {
  if (!startedAt || !completedAt) return "—"
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime()
  if (ms < 0) return "—"
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes === 0) return `${seconds}s`
  return `${minutes}m ${seconds}s`
}

function isAzureDevOpsProvider(provider: string): boolean {
  return provider === "azure-devops" || provider === "azure_devops"
}

function isGitLabProvider(provider: string): boolean {
  return provider === "gitlab"
}

export function findRepoIntegration(
  repos: RepoIntegration[] | undefined,
  repoFullName: string,
): RepoIntegration | undefined {
  return repos?.find((repo) => repo.repo_full_name === repoFullName)
}

export function countFindingsBySeverity(
  findings: ReviewFinding[],
): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const finding of findings) {
    counts[finding.severity] = (counts[finding.severity] ?? 0) + 1
  }
  return counts
}

export function formatProviderLabel(provider: string): string {
  if (provider === "github") return "GitHub"
  if (isGitLabProvider(provider)) return "GitLab"
  if (isAzureDevOpsProvider(provider)) return "Azure DevOps"
  return provider
}

export function shortSha(sha: string): string {
  return sha.length >= 7 ? sha.slice(0, 7) : sha
}

export function formatLineRange(
  lineStart: number | null,
  lineEnd: number | null,
): string | null {
  if (lineStart == null) return null
  if (lineEnd != null && lineEnd !== lineStart) {
    return `${lineStart}–${lineEnd}`
  }
  return String(lineStart)
}
