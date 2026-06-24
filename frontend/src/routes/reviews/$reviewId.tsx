import { createFileRoute, Link } from "@tanstack/react-router"

import { AppShell } from "@/components/layout/AppShell"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useReview } from "@/hooks/use-reviews"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/reviews/$reviewId")({
  component: ReviewDetailPage,
})

function severityClass(severity: string) {
  switch (severity) {
    case "critical":
      return "bg-destructive/15 text-destructive"
    case "warning":
      return "bg-amber-500/15 text-amber-700 dark:text-amber-400"
    case "info":
      return "bg-blue-500/15 text-blue-700 dark:text-blue-400"
    default:
      return "bg-muted text-muted-foreground"
  }
}

function ReviewDetailPage() {
  const { reviewId } = Route.useParams()
  const review = useReview(reviewId)

  const data = review.data
  const githubUrl = data
    ? `https://github.com/${data.repo_full_name}/pull/${data.pr_number}`
    : null

  return (
    <AppShell title="Review detail">
      <div className="mb-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/repositories">← Back</Link>
        </Button>
      </div>

      {review.isPending ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : review.isError || !data ? (
        <p className="text-destructive text-sm">Review not found.</p>
      ) : (
        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-2">
                {data.repo_full_name}#{data.pr_number}
                <Badge variant="secondary">{data.status}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground space-y-2 text-sm">
              <p>
                Head SHA:{" "}
                <code className="text-foreground text-xs">{data.head_sha}</code>
              </p>
              {githubUrl ? (
                <p>
                  <a
                    href={githubUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    View on GitHub
                  </a>
                </p>
              ) : null}
              {data.error_message ? (
                <p className="text-destructive">{data.error_message}</p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                Findings ({data.findings.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {data.findings.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  {data.status === "pending" || data.status === "running"
                    ? "Review in progress…"
                    : "No findings."}
                </p>
              ) : (
                data.findings.map((finding) => (
                  <div
                    key={finding.id}
                    className="border-b pb-4 last:border-0 last:pb-0"
                  >
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <Badge
                        variant="secondary"
                        className={cn(severityClass(finding.severity))}
                      >
                        {finding.severity}
                      </Badge>
                      <span className="font-medium">{finding.title}</span>
                      {finding.file_path ? (
                        <code className="text-muted-foreground text-xs">
                          {finding.file_path}
                          {finding.line_start ? `:${finding.line_start}` : ""}
                        </code>
                      ) : null}
                    </div>
                    <p className="text-muted-foreground text-sm whitespace-pre-wrap">
                      {finding.body}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </AppShell>
  )
}
