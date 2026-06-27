import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { MeResponse } from "@/api/auth-types"
import { api, apiBaseUrl } from "@/api/client"

export function useMe() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api<MeResponse>("/auth/me"),
    retry: false,
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.clear()
      window.location.href = "/login"
    },
  })
}

export function loginUrl(returnTo?: string) {
  const base = apiBaseUrl()
  const params = returnTo ? `?return_to=${encodeURIComponent(returnTo)}` : ""
  return `${base}/api/v1/auth/login${params}`
}
