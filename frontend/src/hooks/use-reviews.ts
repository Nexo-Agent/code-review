import { useQuery } from "@tanstack/react-query"

import { api } from "@/api/client"
import type { Review, ReviewList } from "@/api/types"

export function useReviews(params?: { status?: string; repo?: string }) {
  const search = new URLSearchParams()
  if (params?.status) search.set("status", params.status)
  if (params?.repo) search.set("repo", params.repo)

  const query = search.toString()
  const path = query ? `/reviews?${query}` : "/reviews"

  return useQuery({
    queryKey: ["reviews", params],
    queryFn: () => api<ReviewList>(path),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? []
      const active = items.some(
        (r) => r.status === "pending" || r.status === "running",
      )
      return active ? 5000 : false
    },
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
