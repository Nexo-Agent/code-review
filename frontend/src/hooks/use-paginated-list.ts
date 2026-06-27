import { useQuery, type UseQueryResult } from "@tanstack/react-query"

import { api } from "@/api/client"
import {
  buildListQuery,
  DEFAULT_PAGE_SIZE,
  type PaginatedList,
} from "@/lib/pagination"

type UsePaginatedListOptions = {
  queryKey: readonly unknown[]
  path: string
  page: number
  filters?: Record<string, string | string[] | undefined | null>
  pageSize?: number
  refetchInterval?:
    | number
    | false
    | ((query: { state: { data?: PaginatedList<unknown> } }) => number | false)
  enabled?: boolean
}

export function usePaginatedList<T>({
  queryKey,
  path,
  page,
  filters,
  pageSize = DEFAULT_PAGE_SIZE,
  refetchInterval,
  enabled = true,
}: UsePaginatedListOptions): UseQueryResult<PaginatedList<T>> {
  const queryString = buildListQuery(page, filters, pageSize)

  return useQuery({
    queryKey: [...queryKey, page, filters, pageSize],
    queryFn: () => api<PaginatedList<T>>(`${path}?${queryString}`),
    placeholderData: (previous) => previous,
    refetchInterval,
    enabled,
  })
}
