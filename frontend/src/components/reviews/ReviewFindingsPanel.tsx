import { useMemo, useState } from "react"

import type { Review, ReviewFinding } from "@/api/types"
import { MarkdownContent } from "@/components/patterns/markdown-content"
import { SeverityBadge } from "@/components/patterns/status-badge"
import { Button } from "@/components/ui/button"
import {
  buildFindingUrl,
  countFindingsBySeverity,
  formatLineRange,
} from "@/lib/review-utils"

const SEVERITY_FILTERS = ["critical", "warning", "info", "suggestion"] as const
type SeverityFilter = "all" | (typeof SEVERITY_FILTERS)[number]
type ViewMode = "list" | "file"

function emptyFindingsMessage(review: Review): string {
  if (review.status === "pending" || review.status === "running") {
    return "Review in progress…"
  }
  if (
    review.status === "completed" &&
    review.findings.length === 0 &&
    review.inline_comments_posted > 0
  ) {
    return "No findings in summary; inline comments were posted to the PR."
  }
  return "No findings."
}

function groupFindingsByFile(
  findings: ReviewFinding[],
): Map<string, ReviewFinding[]> {
  const groups = new Map<string, ReviewFinding[]>()
  for (const finding of findings) {
    const key = finding.file_path ?? "General"
    const bucket = groups.get(key)
    if (bucket) {
      bucket.push(finding)
    } else {
      groups.set(key, [finding])
    }
  }
  return groups
}

function FindingItem({
  review,
  finding,
}: {
  review: Review
  finding: ReviewFinding
}) {
  const lineRange = formatLineRange(finding.line_start, finding.line_end)
  const codeUrl = buildFindingUrl(review, finding)

  return (
    <div className="py-3 first:pt-0">
      <div className="mb-1 flex flex-wrap items-center gap-1.5">
        <SeverityBadge severity={finding.severity} />
        <span className="text-sm font-medium">{finding.title}</span>
        {finding.file_path ? (
          codeUrl ? (
            <a
              href={codeUrl}
              target="_blank"
              rel="noreferrer"
              className="text-primary hover:underline"
            >
              <code className="text-xs">
                {finding.file_path}
                {lineRange ? `:${lineRange}` : ""}
              </code>
            </a>
          ) : (
            <code className="text-muted-foreground text-xs">
              {finding.file_path}
              {lineRange ? `:${lineRange}` : ""}
            </code>
          )
        ) : null}
      </div>
      <MarkdownContent content={finding.body} />
    </div>
  )
}

export function ReviewFindingsPanel({ review }: { review: Review }) {
  const [severity, setSeverity] = useState<SeverityFilter>("all")
  const [viewMode, setViewMode] = useState<ViewMode>("list")

  const filtered = useMemo(() => {
    if (severity === "all") return review.findings
    return review.findings.filter((f) => f.severity === severity)
  }, [review.findings, severity])

  const grouped = useMemo(
    () => groupFindingsByFile(filtered),
    [filtered],
  )

  const severityCounts = useMemo(
    () => countFindingsBySeverity(review.findings),
    [review.findings],
  )

  const severityButtons = useMemo(
    () =>
      SEVERITY_FILTERS.filter((value) => (severityCounts[value] ?? 0) > 0),
    [severityCounts],
  )

  return (
    <section className="min-w-0">
      <div className="mb-4 flex flex-col gap-3">
        <h2 className="text-sm font-medium">
          Findings ({review.findings.length})
        </h2>
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <div className="flex flex-wrap gap-1">
            <Button
              type="button"
              size="sm"
              variant={severity === "all" ? "default" : "outline"}
              className="h-7 px-2 text-xs"
              onClick={() => setSeverity("all")}
            >
              All ({review.findings.length})
            </Button>
            {severityButtons.map((value) => (
              <Button
                key={value}
                type="button"
                size="sm"
                variant={severity === value ? "default" : "outline"}
                className="h-7 px-2 text-xs capitalize"
                onClick={() => setSeverity(value)}
              >
                {value} ({severityCounts[value]})
              </Button>
            ))}
          </div>
          <div className="flex gap-1">
            <Button
              type="button"
              size="sm"
              variant={viewMode === "list" ? "default" : "outline"}
              className="h-7 px-2 text-xs"
              onClick={() => setViewMode("list")}
            >
              List
            </Button>
            <Button
              type="button"
              size="sm"
              variant={viewMode === "file" ? "default" : "outline"}
              className="h-7 px-2 text-xs"
              onClick={() => setViewMode("file")}
            >
              By file
            </Button>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted-foreground py-3 text-sm">
          {emptyFindingsMessage(review)}
        </p>
      ) : viewMode === "list" ? (
        <div className="divide-border/60 divide-y">
          {filtered.map((finding) => (
            <FindingItem
              key={finding.id}
              review={review}
              finding={finding}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {[...grouped.entries()].map(([filePath, findings]) => (
            <div key={filePath}>
              <h3 className="text-muted-foreground mb-1 text-xs font-medium">
                {filePath}
              </h3>
              <div className="divide-border/60 divide-y">
                {findings.map((finding) => (
                  <FindingItem
                    key={finding.id}
                    review={review}
                    finding={finding}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
