import type { UseQueryResult } from "@tanstack/react-query"
import type { ReactNode } from "react"

import { InlineError } from "@/components/patterns/inline-error"
import { ListPagination } from "@/components/patterns/list-pagination"
import { Skeleton } from "@/components/ui/skeleton"
import {
  DEFAULT_PAGE_SIZE,
  type PaginatedList,
} from "@/lib/pagination"

type PaginatedListPanelProps<T> = {
  query: UseQueryResult<PaginatedList<T>>
  page: number
  onPageChange: (page: number) => void
  pageSize?: number
  children: (items: T[]) => ReactNode
}

export function PaginatedListPanel<T>({
  query,
  page,
  onPageChange,
  pageSize = DEFAULT_PAGE_SIZE,
  children,
}: PaginatedListPanelProps<T>) {
  const items = query.data?.items ?? []
  const total = query.data?.total ?? 0
  const effectiveTotal = total > 0 ? total : items.length

  if (query.isPending) {
    return (
      <div className="rounded-lg border bg-card">
        <div className="flex flex-col gap-1.5 p-4">
          <Skeleton className="h-7 w-full" />
          <Skeleton className="h-7 w-full" />
          <Skeleton className="h-7 w-full" />
        </div>
      </div>
    )
  }

  if (query.isError) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <InlineError message="Something went wrong." />
      </div>
    )
  }

  return (
    <div className="flex flex-col rounded-lg border bg-card">
      {children(items)}
      <ListPagination
        page={page}
        total={effectiveTotal}
        pageSize={pageSize}
        onPageChange={onPageChange}
        isFetching={query.isFetching}
      />
    </div>
  )
}
