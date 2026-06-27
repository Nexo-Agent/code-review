import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/api/client"
import type { Review, ReviewList } from "@/api/types"

export function useReviews(params?: {
  status?: string
  repo?: string
  pr?: number
}) {
  const search = new URLSearchParams()
  if (params?.status) search.set("status", params.status)
  if (params?.repo) search.set("repo", params.repo)
  if (params?.pr != null) search.set("pr", String(params.pr))

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
