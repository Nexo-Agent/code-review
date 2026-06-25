import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useRereviewReview, useReview } from "@/hooks/use-reviews"
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
  const navigate = useNavigate()
  const review = useReview(reviewId)
  const rereview = useRereviewReview()

  const data = review.data
  const githubUrl = data
    ? `https://github.com/${data.repo_full_name}/pull/${data.pr_number}`
    : null

  const canRereview =
    data?.status === "completed" || data?.status === "failed"

  async function handleRereview() {
    if (!data) return
    try {
      const next = await rereview.mutateAsync(data.id)
      toast.success("Review queued")
      if (next.id !== data.id) {
        await navigate({
          to: "/reviews/$reviewId",
          params: { reviewId: next.id },
        })
      }
    } catch {
      toast.error("Could not start re-review")
    }
  }

  const pageTitle = data
    ? `${data.repo_full_name}#${data.pr_number}`
    : "Review"

  return (
    <AppShell
      title={pageTitle}
      description={data?.pr_title?.trim() || undefined}
      backTo={{ to: "/repositories", label: "Repositories" }}
      actions={
        data && canRereview ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRereview}
            disabled={rereview.isPending}
          >
            <RefreshCw
              className={cn("size-3.5", rereview.isPending && "animate-spin")}
            />
            Re-review
          </Button>
        ) : data ? (
          <Badge variant="secondary">{data.status}</Badge>
        ) : undefined
      }
    >
      {review.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : review.isError || !data ? (
        <p className="text-destructive text-sm">Review not found.</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
            <span>
              SHA{" "}
              <code className="text-foreground">{data.head_sha.slice(0, 7)}</code>
            </span>
            {githubUrl ? (
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline"
              >
                View on GitHub
              </a>
            ) : null}
            {data.error_message ? (
              <span className="text-destructive">{data.error_message}</span>
            ) : null}
          </div>

          <div className="rounded-lg border">
            <div className="flex items-center justify-between border-b px-3 py-2">
              <h2 className="text-sm font-medium">
                Findings ({data.findings.length})
              </h2>
            </div>
            <div className="divide-y">
              {data.findings.length === 0 ? (
                <p className="text-muted-foreground p-3 text-sm">
                  {data.status === "pending" || data.status === "running"
                    ? "Review in progress…"
                    : "No findings."}
                </p>
              ) : (
                data.findings.map((finding) => (
                  <div key={finding.id} className="px-3 py-2.5">
                    <div className="mb-1 flex flex-wrap items-center gap-1.5">
                      <Badge
                        variant="secondary"
                        className={cn(
                          "h-5 px-1.5 text-[10px]",
                          severityClass(finding.severity),
                        )}
                      >
                        {finding.severity}
                      </Badge>
                      <span className="text-sm font-medium">
                        {finding.title}
                      </span>
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
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}
