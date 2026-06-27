import { Link } from "@tanstack/react-router"

import type { Review } from "@/api/types"
import { StatusBadge } from "@/components/patterns/status-badge"
import { Card, CardContent } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useReviews } from "@/hooks/use-reviews"
import { formatReviewTimestamp, shortSha } from "@/lib/review-utils"
import { cn } from "@/lib/utils"

function lastRunAt(review: Review): string {
  const ts = review.completed_at ?? review.started_at
  return formatReviewTimestamp(ts)
}

export function ReviewRunsPanel({
  review,
}: {
  review: Review
}) {
  const runs = useReviews({
    repo: review.repo_full_name,
    pr: review.pr_number,
  })

  const allRuns = runs.data?.items ?? []
  if (runs.isPending || allRuns.length <= 1) {
    return null
  }

  return (
    <Card>
      <CardContent className="p-4">
        <h2 className="mb-3 text-sm font-medium">Runs for this PR</h2>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SHA</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Findings</TableHead>
                <TableHead>Last run</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {allRuns.map((run) => (
                <TableRow
                  key={run.id}
                  className={cn(run.id === review.id && "bg-muted/40")}
                >
                  <TableCell>
                    {run.id === review.id ? (
                      <code className="text-xs">{shortSha(run.head_sha)}</code>
                    ) : (
                      <Link
                        to="/reviews/$reviewId"
                        params={{ reviewId: run.id }}
                        className="text-primary hover:underline"
                      >
                        <code className="text-xs">{shortSha(run.head_sha)}</code>
                      </Link>
                    )}
                    {run.id === review.id ? (
                      <span className="text-muted-foreground ml-1.5 text-xs">
                        current
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={run.status} />
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {run.findings_count}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                    {lastRunAt(run)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
