import { Link } from "@tanstack/react-router"

import type { DashboardReviewsSection } from "@/api/dashboard-types"
import { DataPanel } from "@/components/patterns/data-panel"
import { StatusBadge } from "@/components/patterns/status-badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { DEFAULT_REVIEWS_SEARCH } from "@/lib/pagination"
import { cn } from "@/lib/utils"

function reviewTimestamp(review: DashboardReviewsSection["recent"][number]): string {
  const ts = review.completed_at ?? review.started_at ?? review.created_at
  return new Date(ts).toLocaleString()
}

const STATUS_ACCENT_CLASS: Record<string, string> = {
  pending: "border-l-muted-foreground/60",
  running: "border-l-sky-500",
  failed: "border-l-destructive",
  completed: "border-l-emerald-500",
}

function StatusCount({
  label,
  count,
  status,
}: {
  label: string
  count: number
  status?: string
}) {
  const content = (
    <div
      className={cn(
        "flex h-full min-h-24 flex-col justify-center rounded-lg border border-border/70 border-l-4 px-4 py-3",
        status ? STATUS_ACCENT_CLASS[status] : undefined,
      )}
    >
      <p className="text-muted-foreground text-[11px] font-semibold tracking-[0.16em] uppercase">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{count}</p>
    </div>
  )

  if (!status || count === 0) {
    return <div className="h-full">{content}</div>
  }

  return (
    <Link
      to="/reviews"
      search={{ ...DEFAULT_REVIEWS_SEARCH, status }}
      className="block h-full transition-opacity hover:opacity-80"
    >
      {content}
    </Link>
  )
}

export function DashboardReviewActivity({
  reviews,
  loading,
  error,
}: {
  reviews: DashboardReviewsSection | undefined
  loading?: boolean
  error?: boolean
}) {
  const byStatus = reviews?.by_status

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,280px)_minmax(0,1fr)] lg:items-stretch">
      <Card className="border-border/70 flex h-full flex-col shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Review status</CardTitle>
          <CardDescription>
            {reviews?.total ?? 0} total reviews in your scope
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col">
          <DataPanel
            loading={loading}
            error={error}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="grid h-full flex-1 auto-rows-fr gap-2 sm:grid-cols-2">
              <StatusCount
                label="Pending"
                count={byStatus?.pending ?? 0}
                status="pending"
              />
              <StatusCount
                label="Running"
                count={byStatus?.running ?? 0}
                status="running"
              />
              <StatusCount
                label="Failed"
                count={byStatus?.failed ?? 0}
                status="failed"
              />
              <StatusCount
                label="Completed"
                count={byStatus?.completed ?? 0}
                status="completed"
              />
            </div>
          </DataPanel>
        </CardContent>
      </Card>

      <Card className="border-border/70 flex h-full flex-col shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm font-medium">Recent reviews</CardTitle>
              <CardDescription>Latest activity in your accessible teams</CardDescription>
            </div>
            <Link
              to="/reviews"
              search={DEFAULT_REVIEWS_SEARCH}
              className="text-muted-foreground hover:text-foreground text-xs font-medium"
            >
              View all
            </Link>
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col p-0">
          <DataPanel
            loading={loading}
            error={error}
            className="flex min-h-0 flex-1 flex-col"
          >
            {(reviews?.recent.length ?? 0) === 0 ? (
              <p className="text-muted-foreground flex flex-1 items-center px-4 py-6 text-sm">
                No reviews yet. Connect a repository to start receiving automated
                reviews.
              </p>
            ) : (
              <div className="flex flex-1 flex-col">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pull request</TableHead>
                      <TableHead>Repository</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Updated</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reviews?.recent.map((review) => (
                      <TableRow key={review.id}>
                        <TableCell>
                          <Link
                            to="/reviews/$reviewId"
                            params={{ reviewId: review.id }}
                            className="hover:underline"
                          >
                            <span className="font-medium">
                              #{review.pr_number}
                            </span>
                            {review.pr_title ? (
                              <span className="text-muted-foreground ml-1.5">
                                {review.pr_title}
                              </span>
                            ) : null}
                          </Link>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {review.repo_full_name}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={review.status} />
                        </TableCell>
                        <TableCell className="text-muted-foreground text-right text-xs">
                          {reviewTimestamp(review)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </DataPanel>
        </CardContent>
      </Card>
    </div>
  )
}
