import { useQuery } from "@tanstack/react-query"

import { api } from "@/api/client"
import type {
  UsageBreakdown,
  UsageFilters,
  UsageHistory,
  UsageMetricKey,
  UsageSummary,
} from "@/api/usage-types"

function buildUsageSearchParams(filters: UsageFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.team_id) {
    params.set("team_id", filters.team_id)
  }
  if (filters.repo_integration_id) {
    params.set("repo_integration_id", filters.repo_integration_id)
  }
  if (filters.git_provider) {
    params.set("git_provider", filters.git_provider)
  }
  if (filters.llm_provider_id) {
    params.set("llm_provider_id", filters.llm_provider_id)
  }
  if (filters.start && filters.end) {
    params.set("start", filters.start)
    params.set("end", filters.end)
  } else if (filters.days) {
    const end = new Date()
    const start = new Date(end.getTime() - (filters.days - 1) * 24 * 60 * 60 * 1000)
    params.set(
      "start",
      `${start.toISOString().slice(0, 10)}T00:00:00.000Z`,
    )
    params.set("end", `${end.toISOString().slice(0, 10)}T23:59:59.999Z`)
  }
  return params
}

export function useUsageSummary(filters: UsageFilters) {
  const params = buildUsageSearchParams(filters)
  return useQuery({
    queryKey: ["usage", "summary", filters],
    queryFn: () => api<UsageSummary>(`/usage/summary?${params.toString()}`),
    retry: false,
  })
}

export function useUsageHistory(filters: UsageFilters & { metric: UsageMetricKey }) {
  const params = buildUsageSearchParams(filters)
  params.set("metric", filters.metric)
  return useQuery({
    queryKey: ["usage", "history", filters],
    queryFn: () => api<UsageHistory>(`/usage/history?${params.toString()}`),
    retry: false,
  })
}

export function useUsageBreakdown(
  filters: UsageFilters & { group_by: "team" | "repo" | "llm_provider" },
) {
  const params = buildUsageSearchParams(filters)
  params.set("group_by", filters.group_by)
  return useQuery({
    queryKey: ["usage", "breakdown", filters],
    queryFn: () => api<UsageBreakdown>(`/usage/breakdown?${params.toString()}`),
    retry: false,
  })
}
