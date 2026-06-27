import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import { useMemo, useState } from "react"

import type { Review } from "@/api/types"
import { AppShell } from "@/components/layout/AppShell"
import { BackLink } from "@/components/patterns/back-link"
import { DataPanel } from "@/components/patterns/data-panel"
import { EmptyState } from "@/components/patterns/empty-state"
import { StatusBadge } from "@/components/patterns/status-badge"
import { RepoIntegrationDialog } from "@/components/settings/RepoIntegrationDialog"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useProjectRepo } from "@/hooks/use-settings"
import { useReviews } from "@/hooks/use-reviews"
import { cn } from "@/lib/utils"

export const Route = createFileRoute(
  "/teams/$teamId/projects/$projectId/repos/$repoId",
)({
  component: RepositoryDetailPage,
})

function lastRunAt(review: Review): string {
  const ts = review.completed_at ?? review.started_at
  if (!ts) return "—"
  return new Date(ts).toLocaleString()
}

function RepositoryDetailPage() {
  const { teamId, projectId, repoId } = Route.useParams()
  const navigate = useNavigate()
  const repoQuery = useProjectRepo(teamId, projectId, repoId)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsSession, setSettingsSession] = useState(0)

  const repo = repoQuery.data
  const reviews = useReviews(
    repo?.repo_full_name ? { repo: repo.repo_full_name } : undefined,
  )

  const reviewColumns = useMemo<ColumnDef<Review>[]>(
    () => [
      {
        accessorKey: "pr_number",
        header: "PR #",
        cell: ({ row }) => (
          <Link
            to="/reviews/$reviewId"
            params={{ reviewId: row.original.id }}
            className="font-medium hover:underline"
          >
            #{row.original.pr_number}
          </Link>
        ),
      },
      {
        accessorKey: "pr_title",
        header: "PR name",
        cell: ({ row }) => {
          const title = row.original.pr_title.trim()
          if (!title) {
            return <span className="text-muted-foreground">—</span>
          }
          return (
            <Link
              to="/reviews/$reviewId"
              params={{ reviewId: row.original.id }}
              className="hover:underline"
              title={title}
            >
              <span className="line-clamp-1">{title}</span>
            </Link>
          )
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        accessorKey: "findings_count",
        header: "Findings",
        cell: ({ row }) => {
          const count = row.original.findings_count
          return (
            <span
              className={cn(
                "tabular-nums",
                count === 0 && "text-muted-foreground",
              )}
            >
              {count}
            </span>
          )
        },
      },
      {
        id: "last_run",
        header: "Last run",
        cell: ({ row }) => (
          <span className="text-muted-foreground whitespace-nowrap text-xs">
            {lastRunAt(row.original)}
          </span>
        ),
      },
    ],
    [],
  )

  const reviewTable = useReactTable({
    data: reviews.data?.items ?? [],
    columns: reviewColumns,
    getCoreRowModel: getCoreRowModel(),
  })

  const title = repo
    ? repo.repo_full_name || repo.name || "All repositories"
    : "Repository"

  return (
    <AppShell
      title={title}
      description={repo?.name || undefined}
      actions={
        repo ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setSettingsSession((session) => session + 1)
              setSettingsOpen(true)
            }}
          >
            Settings
          </Button>
        ) : null
      }
    >
      <BackLink
        to="/teams/$teamId/projects/$projectId"
        params={{ teamId, projectId }}
        label="Project"
      />

      {repo ? (
        <RepoIntegrationDialog
          teamId={teamId}
          projectId={projectId}
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
          repo={repo}
          sessionKey={settingsSession}
          onDeleted={() =>
            navigate({
              to: "/teams/$teamId/projects/$projectId",
              params: { teamId, projectId },
            })
          }
        />
      ) : null}

      {repoQuery.isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : repoQuery.isError || !repo ? (
        <p className="text-destructive text-sm">Repository not found.</p>
      ) : (
        <DataPanel
          loading={reviews.isPending}
          error={reviews.isError}
          errorMessage="Could not load reviews."
        >
          <Table>
            <TableHeader>
              {reviewTable.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {reviewTable.getRowModel().rows.length ? (
                reviewTable.getRowModel().rows.map((row) => (
                  <TableRow key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <EmptyState colSpan={reviewColumns.length}>
                  No reviews yet for this repository.
                </EmptyState>
              )}
            </TableBody>
          </Table>
        </DataPanel>
      )}
    </AppShell>
  )
}
