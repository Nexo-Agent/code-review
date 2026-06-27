import { createFileRoute, Link } from "@tanstack/react-router"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import { useMemo, useState } from "react"

import type { Review } from "@/api/types"
import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { EmptyState } from "@/components/patterns/empty-state"
import { CodeHint } from "@/components/patterns/inline-error"
import { MultiSelectFilter } from "@/components/patterns/multi-select-filter"
import { StatusBadge } from "@/components/patterns/status-badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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

const STATUS_OPTIONS = [
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
] as const

function lastRunAt(review: Review): string {
  const ts = review.completed_at ?? review.started_at
  if (!ts) return "—"
  return new Date(ts).toLocaleString()
}

function reviewSearchText(review: Review): string {
  return [
    String(review.pr_number),
    review.pr_title,
    review.repo_full_name,
    review.pr_author,
    review.status,
    review.head_ref,
    review.base_ref,
  ]
    .join(" ")
    .toLowerCase()
}

function ReviewsPage() {
  const reviews = useReviews()
  const reviewList = reviews.data?.items ?? []

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [repoFilter, setRepoFilter] = useState<string[]>([])

  const repoOptions = useMemo(
    () => [...new Set(reviewList.map((review) => review.repo_full_name))].toSorted(),
    [reviewList],
  )

  const filteredReviews = useMemo(() => {
    const query = search.trim().toLowerCase()
    return reviewList.filter((review) => {
      if (statusFilter !== "all" && review.status !== statusFilter) {
        return false
      }
      if (repoFilter.length > 0 && !repoFilter.includes(review.repo_full_name)) {
        return false
      }
      if (query && !reviewSearchText(review).includes(query)) {
        return false
      }
      return true
    })
  }, [reviewList, search, statusFilter, repoFilter])

  const hasFilters =
    search.trim() !== "" || statusFilter !== "all" || repoFilter.length > 0

  const description = hasFilters
    ? `${filteredReviews.length} of ${reviewList.length} pull request review${reviewList.length === 1 ? "" : "s"}`
    : `${reviewList.length} pull request review${reviewList.length === 1 ? "" : "s"}`

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
    data: filteredReviews,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <AppShell title="Reviews" description={description}>
      <div className="mb-4 flex flex-col gap-3">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search PR #, title, repository, author…"
          className="max-w-md"
        />
        <div className="flex flex-wrap gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="all">All status</SelectItem>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>

          <MultiSelectFilter
            options={repoOptions.map((repo) => ({ value: repo, label: repo }))}
            selected={repoFilter}
            onSelectedChange={setRepoFilter}
            emptyLabel="All repositories"
            searchPlaceholder="Search repositories…"
            className="w-56"
          />
        </div>
      </div>

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
                {reviewList.length ? (
                  "No reviews match your search or filters."
                ) : (
                  <>
                    No reviews yet — configure a GitHub webhook to{" "}
                    <CodeHint>/api/v1/webhooks/github</CodeHint>
                  </>
                )}
              </EmptyState>
            )}
          </TableBody>
        </Table>
      </DataPanel>
    </AppShell>
  )
}
