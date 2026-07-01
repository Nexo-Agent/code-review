import { useQuery } from "@tanstack/react-query"

import type { DashboardSummary } from "@/api/dashboard-types"
import { api } from "@/api/client"

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api<DashboardSummary>("/dashboard/summary"),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return false
      const active =
        data.reviews.by_status.pending > 0 || data.reviews.by_status.running > 0
      return active ? 5000 : false
    },
  })
}
