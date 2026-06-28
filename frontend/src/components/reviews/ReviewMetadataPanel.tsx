import { Link } from "@tanstack/react-router"
import type { LucideIcon } from "lucide-react"
import {
  ChevronDown,
  Copy,
  ExternalLink,
  FolderGit2,
  GitBranch,
  GitCommitHorizontal,
  MessageSquare,
  User,
} from "lucide-react"
import type { ReactNode } from "react"
import { useState } from "react"
import { toast } from "sonner"

import type { RepoIntegration } from "@/api/settings-types"
import type { Review } from "@/api/types"
import { StatusBadge } from "@/components/patterns/status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  formatDuration,
  formatProviderLabel,
} from "@/lib/review-utils"
import { cn } from "@/lib/utils"

function MetadataSection({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="border-border/60 border-t pt-3">
      <h3 className="text-muted-foreground mb-2 text-[11px] font-medium tracking-wide uppercase">
        {title}
      </h3>
      <div className="flex flex-col gap-0.5">{children}</div>
    </section>
  )
}

function MetadataRow({
  icon: Icon,
  label,
  children,
  mono,
}: {
  icon: LucideIcon
  label: string
  children: ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <Icon className="text-muted-foreground mt-0.5 size-3.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="text-muted-foreground text-[11px]">{label}</div>
        <div
          className={cn(
            "text-sm leading-snug break-words",
            mono && "font-mono text-xs",
          )}
        >
          {children}
        </div>
      </div>
    </div>
  )
}

function CopyableValue({
  value,
  label,
  display,
}: {
  value: string
  label: string
  display?: string
}) {
  return (
    <span className="inline-flex max-w-full items-center gap-1">
      <span className="truncate">{display ?? value}</span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-6 shrink-0"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(value)
            toast.success(`${label} copied`)
          } catch {
            toast.error(`Could not copy ${label}`)
          }
        }}
      >
        <Copy className="size-3" />
      </Button>
    </span>
  )
}

function DeliveryStat({
  label,
  value,
  ok,
}: {
  label: string
  value: string | number
  ok?: boolean
}) {
  return (
    <div className="bg-muted/50 rounded-md px-2.5 py-2 text-center">
      <div
        className={cn(
          "text-sm font-semibold tabular-nums",
          ok === true && "text-success-foreground",
          ok === false && "text-muted-foreground",
        )}
      >
        {value}
      </div>
      <div className="text-muted-foreground text-[10px] leading-tight">
        {label}
      </div>
    </div>
  )
}

export function ReviewMetadataPanel({
  review,
  repoIntegration,
}: {
  review: Review
  repoIntegration?: RepoIntegration
}) {
  const [debugOpen, setDebugOpen] = useState(false)
  const prUrl = review.pr_url?.trim() || null
  const prTitle = review.pr_title.trim()
  const branchLabel =
    review.base_ref && review.head_ref
      ? `${review.base_ref} ← ${review.head_ref}`
      : review.head_ref || review.base_ref || null
  const duration = formatDuration(review.started_at, review.completed_at)
  const showDelivery =
    review.status === "completed" &&
    (review.summary_comment_posted ||
      review.inline_comments_posted > 0 ||
      review.inline_comments_skipped > 0)

  return (
    <div className="flex flex-col gap-3">
      {review.error_message ? (
        <div className="border-destructive/30 bg-destructive/5 text-destructive rounded-lg border px-3 py-2.5 text-sm">
          {review.error_message}
        </div>
      ) : null}

      <Card className="border-border/60 border">
        <CardContent className="space-y-3 p-4">
          <div className="space-y-2.5">
            <div className="space-y-1">
              <p className="text-muted-foreground text-xs font-medium">
                Pull request #{review.pr_number}
              </p>
              {prTitle ? (
                <p className="text-sm leading-snug font-medium">{prTitle}</p>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center gap-1.5">
              <StatusBadge status={review.status} />
              <Badge variant="outline" className="h-5 px-1.5 text-[10px]">
                {formatProviderLabel(review.provider)}
              </Badge>
              {duration !== "—" ? (
                <Badge variant="muted" className="h-5 px-1.5 text-[10px]">
                  {duration}
                </Badge>
              ) : null}
            </div>

            {prUrl ? (
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-full justify-center gap-1.5 text-xs"
                asChild
              >
                <a href={prUrl} target="_blank" rel="noreferrer">
                  <ExternalLink className="size-3.5" />
                  Open on {formatProviderLabel(review.provider)}
                </a>
              </Button>
            ) : null}
          </div>

          <MetadataSection title="Repository">
            <MetadataRow icon={FolderGit2} label="Repository">
              {repoIntegration ? (
                <Link
                  to="/repositories/$repoId"
                  params={{ repoId: repoIntegration.id }}
                  className="text-primary hover:underline"
                >
                  {review.repo_full_name}
                </Link>
              ) : (
                review.repo_full_name
              )}
            </MetadataRow>
            {review.pr_author ? (
              <MetadataRow icon={User} label="Author">
                {review.pr_author}
              </MetadataRow>
            ) : null}
            {branchLabel ? (
              <MetadataRow icon={GitBranch} label="Branches" mono>
                {branchLabel}
              </MetadataRow>
            ) : null}
          </MetadataSection>

          {showDelivery ? (
            <MetadataSection title="Posted to PR">
              <MetadataRow icon={MessageSquare} label="Delivery">
                <div className="mt-1 grid grid-cols-3 gap-1.5">
                  <DeliveryStat
                    label="Summary"
                    value={review.summary_comment_posted ? "Yes" : "No"}
                    ok={review.summary_comment_posted}
                  />
                  <DeliveryStat
                    label="Inline"
                    value={review.inline_comments_posted}
                  />
                  <DeliveryStat
                    label="Skipped"
                    value={review.inline_comments_skipped}
                  />
                </div>
              </MetadataRow>
            </MetadataSection>
          ) : null}
        </CardContent>
      </Card>

      <div className="border-border/60 rounded-lg border">
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground flex w-full items-center justify-between px-3 py-2.5 text-xs font-medium"
          onClick={() => setDebugOpen((open) => !open)}
        >
          Debug
          <ChevronDown
            className={cn(
              "size-3.5 transition-transform",
              debugOpen && "rotate-180",
            )}
          />
        </button>
        {debugOpen ? (
          <div className="border-border/60 space-y-2 border-t px-3 py-2.5">
            <MetadataRow icon={Copy} label="Review ID" mono>
              <CopyableValue value={review.id} label="Review ID" />
            </MetadataRow>
            {review.delivery_id ? (
              <MetadataRow icon={Copy} label="Delivery ID" mono>
                <CopyableValue
                  value={review.delivery_id}
                  label="Delivery ID"
                />
              </MetadataRow>
            ) : null}
            <MetadataRow icon={GitCommitHorizontal} label="Head SHA" mono>
              <CopyableValue value={review.head_sha} label="Head SHA" />
            </MetadataRow>
            {review.base_sha ? (
              <MetadataRow icon={GitCommitHorizontal} label="Base SHA" mono>
                <CopyableValue value={review.base_sha} label="Base SHA" />
              </MetadataRow>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}
