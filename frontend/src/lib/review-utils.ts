import type { RepoIntegration } from "@/api/settings-types"
import type { Review, ReviewFinding } from "@/api/types"

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

export function isAzureDevOpsProvider(provider: string): boolean {
  return provider === "azure-devops" || provider === "azure_devops"
}

export function buildAzureDevOpsPrUrl(
  repoFullName: string,
  prNumber: number,
): string | null {
  const parts = repoFullName.split("/").map((part) => part.trim()).filter(Boolean)
  if (parts.length < 3) return null
  const [organization, project, repo] = parts
  return `https://dev.azure.com/${organization}/${project}/_git/${repo}/pullrequest/${prNumber}`
}

export function buildPrUrl(review: Pick<
  Review,
  "provider" | "repo_full_name" | "pr_number" | "pr_url"
>): string | null {
  if (review.pr_url?.trim()) return review.pr_url.trim()
  if (review.provider === "github") {
    return `https://github.com/${review.repo_full_name}/pull/${review.pr_number}`
  }
  if (isAzureDevOpsProvider(review.provider)) {
    return buildAzureDevOpsPrUrl(review.repo_full_name, review.pr_number)
  }
  return null
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
  if (isAzureDevOpsProvider(provider)) return "Azure DevOps"
  return provider
}

export function shortSha(sha: string): string {
  return sha.length >= 7 ? sha.slice(0, 7) : sha
}

export function buildFindingUrl(
  review: Pick<
    Review,
    "provider" | "repo_full_name" | "pr_number" | "head_sha" | "pr_url"
  >,
  finding: Pick<ReviewFinding, "file_path" | "line_start">,
): string | null {
  if (!finding.file_path) return null
  const line = finding.line_start
  if (review.provider === "github") {
    const base = `https://github.com/${review.repo_full_name}/blob/${review.head_sha}/${finding.file_path}`
    return line ? `${base}#L${line}` : base
  }
  const prUrl = buildPrUrl(review)
  if (prUrl) return prUrl
  return null
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
