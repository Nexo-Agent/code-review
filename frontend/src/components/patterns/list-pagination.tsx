import { Button } from "@/components/ui/button"
import {
  DEFAULT_PAGE_SIZE,
  pageRange,
  totalPages,
} from "@/lib/pagination"

type ListPaginationProps = {
  page: number
  total: number
  pageSize?: number
  onPageChange: (page: number) => void
  isFetching?: boolean
}

export function ListPagination({
  page,
  total,
  pageSize = DEFAULT_PAGE_SIZE,
  onPageChange,
  isFetching = false,
}: ListPaginationProps) {
  if (total <= 0) {
    return null
  }

  const pages = totalPages(total, pageSize)
  const { start, end } = pageRange(page, total, pageSize)
  const canGoBack = page > 1
  const canGoForward = page < pages

  return (
    <div className="border-t bg-muted/20">
      <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground text-sm">
          Showing {start}–{end} of {total}
        </p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!canGoBack || isFetching}
            onClick={() => onPageChange(page - 1)}
          >
            Previous
          </Button>
          <span className="text-muted-foreground min-w-24 text-center text-sm">
            Page {page} of {pages}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!canGoForward || isFetching}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
