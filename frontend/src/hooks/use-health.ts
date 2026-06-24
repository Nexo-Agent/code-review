import { useQuery } from "@tanstack/react-query"

import { api } from "@/api/client"
import type { HealthResponse } from "@/api/types"

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api<HealthResponse>("/health"),
  })
}
