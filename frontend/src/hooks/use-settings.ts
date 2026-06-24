import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/api/client"
import type {
  LlmProvider,
  LlmProviderCreate,
  LlmProviderUpdate,
  RepoIntegration,
  RepoIntegrationCreate,
  RepoIntegrationUpdate,
} from "@/api/settings-types"

export function useLlmProviders() {
  return useQuery({
    queryKey: ["settings", "llm-providers"],
    queryFn: () => api<LlmProvider[]>("/settings/llm-providers"),
  })
}

export function useCreateLlmProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: LlmProviderCreate) =>
      api<LlmProvider>("/settings/llm-providers", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "llm-providers"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useUpdateLlmProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: LlmProviderUpdate
    }) =>
      api<LlmProvider>(`/settings/llm-providers/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "llm-providers"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useDeleteLlmProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api<void>(`/settings/llm-providers/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "llm-providers"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useRepoIntegrations() {
  return useQuery({
    queryKey: ["settings", "repos"],
    queryFn: () => api<RepoIntegration[]>("/settings/repos"),
  })
}

export function useRepoIntegration(id: string) {
  const query = useRepoIntegrations()
  return {
    ...query,
    data: query.data?.find((repo) => repo.id === id),
  }
}

export function useLlmProvider(id: string) {
  const query = useLlmProviders()
  return {
    ...query,
    data: query.data?.find((provider) => provider.id === id),
  }
}

export function useCreateRepoIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: RepoIntegrationCreate) =>
      api<RepoIntegration>("/settings/repos", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useUpdateRepoIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: RepoIntegrationUpdate
    }) =>
      api<RepoIntegration>(`/settings/repos/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useDeleteRepoIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api<void>(`/settings/repos/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}
