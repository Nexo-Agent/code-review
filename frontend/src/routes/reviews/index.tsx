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
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useReviews } from "@/hooks/use-reviews"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/reviews/")({
  component: ReviewsPage,
})

function statusClass(status: string) {
  switch (status) {
    case "completed":
      return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
    case "failed":
      return "bg-destructive/15 text-destructive"
    case "running":
      return "bg-blue-500/15 text-blue-700 dark:text-blue-400"
    default:
      return "bg-muted text-muted-foreground"
  }
}

function ReviewsPage() {
  const reviews = useReviews()

  const columns = useMemo<ColumnDef<Review>[]>(
    () => [
      {
        accessorKey: "repo_full_name",
        header: "Repository",
        cell: ({ row }) => (
          <Link
            to="/reviews/$reviewId"
            params={{ reviewId: row.original.id }}
            className="font-medium hover:underline"
          >
            {row.original.repo_full_name}
          </Link>
        ),
      },
      { accessorKey: "pr_number", header: "PR #" },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge
            variant="secondary"
            className={cn(statusClass(row.original.status))}
          >
            {row.original.status}
          </Badge>
        ),
      },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ row }) =>
          new Date(row.original.created_at).toLocaleString(),
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
    <AppShell title="Reviews">
      <Card>
        <CardHeader>
          <CardTitle>Pull request reviews</CardTitle>
        </CardHeader>
        <CardContent>
          {reviews.isPending ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : reviews.isError ? (
            <p className="text-destructive text-sm">
              Could not load reviews. Run migrations with{" "}
              <code className="text-xs">make migrate</code>.
            </p>
          ) : (
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
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="text-muted-foreground h-16 text-center"
                    >
                      No reviews yet — configure a GitHub webhook to{" "}
                      <code className="text-xs">/api/v1/webhooks/github</code>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  )
}
