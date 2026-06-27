import { createFileRoute, Link } from "@tanstack/react-router"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import { useMemo } from "react"

import type { Review } from "@/api/types"
import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { EmptyState } from "@/components/patterns/empty-state"
import { CodeHint } from "@/components/patterns/inline-error"
import { StatusBadge } from "@/components/patterns/status-badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useReviews } from "@/hooks/use-reviews"

export const Route = createFileRoute("/reviews/")({
  component: ReviewsPage,
})

function lastRunAt(review: Review): string {
  const ts = review.completed_at ?? review.started_at
  if (!ts) return "—"
  return new Date(ts).toLocaleString()
}

function ReviewsPage() {
  const reviews = useReviews()
  const count = reviews.data?.items.length ?? 0

  const columns = useMemo<ColumnDef<Review>[]>(
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
        accessorKey: "repo_full_name",
        header: "Repository",
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.repo_full_name}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
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

  const table = useReactTable({
    data: reviews.data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <AppShell
      title="Reviews"
      description={`${count} pull request review${count === 1 ? "" : "s"}`}
    >
      <DataPanel
        loading={reviews.isPending}
        error={reviews.isError}
        errorMessage="Could not load reviews. Run migrations with"
        errorHint={<CodeHint>make migrate</CodeHint>}
      >
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
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
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
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
              <EmptyState colSpan={columns.length}>
                No reviews yet — configure a GitHub webhook to{" "}
                <CodeHint>/api/v1/webhooks/github</CodeHint>
              </EmptyState>
            )}
          </TableBody>
        </Table>
      </DataPanel>
    </AppShell>
  )
}
