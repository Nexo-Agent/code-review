import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/api/client"
import type {
  IntegrationSettings,
  IntegrationSettingsUpdate,
} from "@/api/types"

export function useIntegrationSettings() {
  return useQuery({
    queryKey: ["settings", "integration"],
    queryFn: () => api<IntegrationSettings>("/settings/integration"),
  })
}

export function useUpdateIntegrationSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: IntegrationSettingsUpdate) =>
      api<IntegrationSettings>("/settings/integration", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "integration"] })
    },
  })
}
