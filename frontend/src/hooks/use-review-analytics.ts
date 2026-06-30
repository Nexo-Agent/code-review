import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/api/client"
import type {
  ReviewAnalyticsHistory,
  ReviewAnalyticsRecomputeRequest,
  ReviewAnalyticsRecomputeResponse,
  ReviewAnalyticsSnapshot,
} from "@/api/types"

export function useReviewAnalytics() {
  return useReviewAnalyticsScoped({ scope: "all" })
}

export function useReviewAnalyticsScoped(params: {
  scope: "all" | "team" | "repo"
  team_id?: string
  repo_integration_id?: string
}) {
  const filters = new URLSearchParams()
  filters.set("scope", params.scope)
  if (params.team_id) {
    filters.set("team_id", params.team_id)
  }
  if (params.repo_integration_id) {
    filters.set("repo_integration_id", params.repo_integration_id)
  }
  return useQuery({
    queryKey: ["reviews", "analytics", params],
    queryFn: () =>
      api<ReviewAnalyticsSnapshot>(`/reviews/analytics?${filters.toString()}`),
    retry: false,
  })
}

export function useRecomputeReviewAnalytics() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ReviewAnalyticsRecomputeRequest) =>
      api<ReviewAnalyticsRecomputeResponse>("/reviews/analytics/recompute", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", "analytics"] })
    },
  })
}

export function useReviewAnalyticsHistory(params: {
  metric_key: string
  scope: "all" | "team" | "repo"
  team_id?: string
  repo_integration_id?: string
  days?: number
  start?: string
  end?: string
}) {
  const filters = new URLSearchParams()
  filters.set("metric_key", params.metric_key)
  filters.set("scope", params.scope)
  if (params.team_id) {
    filters.set("team_id", params.team_id)
  }
  if (params.repo_integration_id) {
    filters.set("repo_integration_id", params.repo_integration_id)
  }
  if (params.start && params.end) {
    filters.set("start", params.start)
    filters.set("end", params.end)
  } else {
    filters.set("days", String(params.days ?? 30))
  }
  return useQuery({
    queryKey: ["reviews", "analytics", "history", params],
    queryFn: () =>
      api<ReviewAnalyticsHistory>(
        `/reviews/analytics/history?${filters.toString()}`,
      ),
    retry: false,
  })
}
