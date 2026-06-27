import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { BackLink } from "@/components/patterns/back-link"
import { ReviewFindingsPanel } from "@/components/reviews/ReviewFindingsPanel"
import { ReviewMetadataPanel } from "@/components/reviews/ReviewMetadataPanel"
import { ReviewRunsPanel } from "@/components/reviews/ReviewRunsPanel"
import {
  StatusBadge,
} from "@/components/patterns/status-badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useRepoIntegrations } from "@/hooks/use-settings"
import { useRereviewReview, useReview } from "@/hooks/use-reviews"
import { findRepoIntegration } from "@/lib/review-utils"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/reviews/$reviewId")({
  component: ReviewDetailPage,
})

function ReviewDetailPage() {
  const { reviewId } = Route.useParams()
  const navigate = useNavigate()
  const review = useReview(reviewId)
  const repos = useRepoIntegrations()
  const rereview = useRereviewReview()

  const data = review.data
  const repoIntegration = data
    ? findRepoIntegration(repos.data, data.repo_full_name)
    : undefined

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

  const prTitle = data?.pr_title?.trim()
  const pageTitle = prTitle || (data ? `#${data.pr_number}` : "Review")
  const pageDescription = data
    ? `${data.repo_full_name} · #${data.pr_number}`
    : undefined

  return (
    <AppShell
      title={pageTitle}
      description={pageDescription}
      mainClassName="flex min-h-0 flex-col overflow-hidden p-0"
      actions={
        data ? (
          <div className="flex items-center gap-2">
            <StatusBadge status={data.status} />
            {canRereview ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleRereview}
                disabled={rereview.isPending}
              >
                <RefreshCw
                  className={cn(
                    "size-3.5",
                    rereview.isPending && "animate-spin",
                  )}
                />
                Re-review
              </Button>
            ) : null}
          </div>
        ) : undefined
      }
    >
      {review.isPending ? (
        <div className="flex min-h-0 flex-1 flex-col gap-4 p-4 lg:flex-row lg:gap-0">
          <Skeleton className="min-h-0 flex-1" />
          <Skeleton className="min-h-0 flex-1 lg:w-80 xl:w-96 lg:shrink-0" />
        </div>
      ) : review.isError || !data ? (
        <p className="text-destructive p-4 text-sm">Review not found.</p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
          <div className="border-border/50 min-h-0 flex-1 overflow-y-auto p-4 lg:border-r">
            <BackLink to="/reviews" label="Reviews" />
            <ReviewFindingsPanel review={data} />
          </div>
          <aside className="border-border/50 flex min-h-0 flex-1 shrink-0 flex-col gap-4 overflow-y-auto border-t p-4 lg:w-80 lg:flex-none lg:border-t-0 xl:w-96">
            <ReviewMetadataPanel
              review={data}
              repoIntegration={repoIntegration}
            />
            <ReviewRunsPanel review={data} />
          </aside>
        </div>
      )}
    </AppShell>
  )
}
