import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type {
  InstallBootstrapPayload,
  InstallStatus,
  LocalLoginPayload,
} from "@/api/install-types"
import type { MeResponse } from "@/api/auth-types"
import { api } from "@/api/client"

export function useInstallStatus() {
  return useQuery({
    queryKey: ["install", "status"],
    queryFn: () => api<InstallStatus>("/install/status"),
    retry: false,
    staleTime: 30_000,
  })
}

export function useInstallBootstrap() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: InstallBootstrapPayload) =>
      api<MeResponse>("/install/bootstrap", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["install", "status"] })
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] })
    },
  })
}

export function useLocalLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: LocalLoginPayload) =>
      api<MeResponse>("/auth/local/login", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (me) => {
      queryClient.setQueryData(["auth", "me"], me)
    },
  })
}
