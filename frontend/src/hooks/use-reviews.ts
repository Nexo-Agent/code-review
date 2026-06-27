import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { Review } from "@/api/types"
import { api } from "@/api/client"
import type { PaginatedList } from "@/lib/pagination"
import { usePaginatedList } from "@/hooks/use-paginated-list"

export function useReviewsPage(params: {
  page: number
  q?: string
  status?: string
  repo?: string[]
  pr?: number
}) {
  const query = params.q?.trim() ?? ""
  const filters: Record<string, string | string[] | undefined> = {}
  if (query) filters.q = query
  if (params.status && params.status !== "all") filters.status = params.status
  if (params.repo?.length) filters.repo = params.repo
  if (params.pr != null) filters.pr = String(params.pr)

  return usePaginatedList<Review>({
    queryKey: ["reviews", filters],
    path: "/reviews",
    page: params.page,
    filters,
    refetchInterval: (queryState) => {
      const data = queryState.state.data as PaginatedList<Review> | undefined
      const items = data?.items ?? []
      const active = items.some(
        (r) => r.status === "pending" || r.status === "running",
      )
      return active ? 5000 : false
    },
  })
}

export function useReviews(params?: {
  status?: string
  repo?: string[]
  pr?: number
}) {
  return useReviewsPage({
    page: 1,
    status: params?.status,
    repo: params?.repo,
    pr: params?.pr,
  })
}

export function useReview(reviewId: string) {
  return useQuery({
    queryKey: ["reviews", reviewId],
    queryFn: () => api<Review>(`/reviews/${reviewId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === "pending" || status === "running" ? 5000 : false
    },
  })
}

export function useRereviewReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (reviewId: string) =>
      api<Review>(`/reviews/${reviewId}/retry`, { method: "POST" }),
    onSuccess: (review) => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] })
      queryClient.setQueryData(["reviews", review.id], review)
    },
  })
}
