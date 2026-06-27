import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type {
  IdentityProvider,
  IdentityProviderPublic,
  IdentityProviderUpsertPayload,
  SamlSpCertUploadPayload,
} from "@/api/identity-provider-types"
import { ApiError, api } from "@/api/client"

export function usePublicIdentityProvider() {
  return useQuery({
    queryKey: ["auth", "idp", "public"],
    queryFn: () => api<IdentityProviderPublic>("/auth/idp"),
    retry: false,
  })
}

export function useIdentityProvider() {
  return useQuery({
    queryKey: ["settings", "identity-provider"],
    queryFn: async () => {
      try {
        return await api<IdentityProvider>("/settings/identity-provider")
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null
        }
        throw error
      }
    },
    retry: false,
  })
}

export function useUpsertIdentityProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: IdentityProviderUpsertPayload) =>
      api<IdentityProvider>("/settings/identity-provider", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "identity-provider"] })
      queryClient.invalidateQueries({ queryKey: ["auth", "idp"] })
    },
  })
}

export function useDeleteIdentityProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api<void>("/settings/identity-provider", { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "identity-provider"] })
      queryClient.invalidateQueries({ queryKey: ["auth", "idp"] })
    },
  })
}

export function useUploadSamlSpCert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: SamlSpCertUploadPayload) =>
      api<IdentityProvider>("/settings/identity-provider/saml/cert", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "identity-provider"] })
    },
  })
}
