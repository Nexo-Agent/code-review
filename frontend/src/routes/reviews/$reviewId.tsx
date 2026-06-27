import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import {
  SeverityBadge,
  StatusBadge,
} from "@/components/patterns/status-badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useRereviewReview, useReview } from "@/hooks/use-reviews"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/reviews/$reviewId")({
  component: ReviewDetailPage,
})

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
      backTo={{ to: "/reviews", label: "Reviews" }}
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
          <StatusBadge status={data.status} />
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
        <div className="flex flex-col gap-4">
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

          <section>
            <h2 className="mb-2 text-sm font-medium">
              Findings ({data.findings.length})
            </h2>
            <div className="divide-border/60 divide-y">
              {data.findings.length === 0 ? (
                <p className="text-muted-foreground py-3 text-sm">
                  {data.status === "pending" || data.status === "running"
                    ? "Review in progress…"
                    : "No findings."}
                </p>
              ) : (
                data.findings.map((finding) => (
                  <div key={finding.id} className="py-3 first:pt-0">
                    <div className="mb-1 flex flex-wrap items-center gap-1.5">
                      <SeverityBadge severity={finding.severity} />
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
          </section>
        </div>
      )}
    </AppShell>
  )
}
