import { createFileRoute, Link } from "@tanstack/react-router"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import { useEffect, useMemo, useState } from "react"

import type { Review } from "@/api/types"
import { AppShell } from "@/components/layout/AppShell"
import { EmptyState } from "@/components/patterns/empty-state"
import { CodeHint } from "@/components/patterns/inline-error"
import { MultiSelectFilter } from "@/components/patterns/multi-select-filter"
import { PaginatedListPanel } from "@/components/patterns/paginated-list-panel"
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
import { useReviewsPage } from "@/hooks/use-reviews"
import { useOrgRepositoriesOptions } from "@/hooks/use-teams"
import { parsePageSearch } from "@/lib/pagination"

const STATUS_OPTIONS = [
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
] as const

type ReviewsSearch = {
  page: number
  q: string
  status: string
  repo: string[]
}

function parseReviewsSearch(search: Record<string, unknown>): ReviewsSearch {
  const base = parsePageSearch(search)
  const status = typeof search.status === "string" ? search.status : "all"
  const repoRaw = search.repo
  const repo =
    typeof repoRaw === "string"
      ? repoRaw.split(",").filter(Boolean)
      : Array.isArray(repoRaw)
        ? repoRaw.filter((value): value is string => typeof value === "string")
        : []
  return { ...base, status, repo }
}

export const Route = createFileRoute("/reviews/")({
  validateSearch: parseReviewsSearch,
  component: ReviewsPage,
})

function lastRunAt(review: Review): string {
  const ts = review.completed_at ?? review.started_at
  if (!ts) return "—"
  return new Date(ts).toLocaleString()
}

function ReviewSearchInput({
  q,
  onQueryChange,
}: {
  q: string
  onQueryChange: (value: string) => void
}) {
  const [searchInput, setSearchInput] = useState(q)

  useEffect(() => {
    const trimmed = searchInput.trim()
    if (trimmed === q) {
      return
    }
    const timeout = window.setTimeout(() => {
      onQueryChange(trimmed)
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [searchInput, q, onQueryChange])

  return (
    <Input
      value={searchInput}
      onChange={(event) => setSearchInput(event.target.value)}
      placeholder="Search PR #, title, repository, author…"
      className="max-w-md"
    />
  )
}

function ReviewsPage() {
  const navigate = Route.useNavigate()
  const { page, q, status, repo } = Route.useSearch()
  const orgRepos = useOrgRepositoriesOptions()
  const reviews = useReviewsPage({ page, q, status, repo })

  const repoOptions = useMemo(() => {
    const names = new Set<string>()
    for (const row of orgRepos.data?.items ?? []) {
      if (row.repo_full_name) {
        names.add(row.repo_full_name)
      }
    }
    return [...names].toSorted()
  }, [orgRepos.data?.items])

  const total = reviews.data?.total ?? 0
  const hasFilters =
    q.trim() !== "" || status !== "all" || repo.length > 0

  const description = hasFilters
    ? `${total} pull request review${total === 1 ? "" : "s"} matching filters`
    : `${total} pull request review${total === 1 ? "" : "s"}`

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

  function goToPage(nextPage: number) {
    void navigate({ search: { page: nextPage, q, status, repo } })
  }

  function updateFilters(
    patch: Partial<Pick<ReviewsSearch, "status" | "repo">>,
  ) {
    void navigate({
      search: {
        page: 1,
        q,
        status: patch.status ?? status,
        repo: patch.repo ?? repo,
      },
    })
  }

  return (
    <AppShell title="Reviews" description={description}>
      <div className="mb-4 flex flex-col gap-3">
        <ReviewSearchInput
          key={q}
          q={q}
          onQueryChange={(trimmed) => {
            void navigate({
              search: { page: 1, q: trimmed, status, repo },
              replace: true,
            })
          }}
        />
        <div className="flex flex-wrap gap-2">
          <Select
            value={status}
            onValueChange={(value) => updateFilters({ status: value })}
          >
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
            options={repoOptions.map((name) => ({ value: name, label: name }))}
            selected={repo}
            onSelectedChange={(next) => updateFilters({ repo: next })}
            emptyLabel="All repositories"
            searchPlaceholder="Search repositories…"
            className="w-56"
          />
        </div>
      </div>

      <PaginatedListPanel
        query={reviews}
        page={page}
        onPageChange={goToPage}
      >
        {(reviewList) => (
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
              {reviewList.length ? (
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
                  {hasFilters ? (
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
        )}
      </PaginatedListPanel>
    </AppShell>
  )
}
