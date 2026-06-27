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
import { usePaginatedList } from "@/hooks/use-paginated-list"

const OPTIONS_PAGE_SIZE = 100

export function useLlmProvidersPage(params: { page: number; q?: string }) {
  const query = params.q?.trim() ?? ""
  return usePaginatedList<LlmProvider>({
    queryKey: ["settings", "llm-providers", query],
    path: "/settings/llm-providers",
    page: params.page,
    filters: query ? { q: query } : undefined,
  })
}

export function useLlmProviders() {
  return usePaginatedList<LlmProvider>({
    queryKey: ["settings", "llm-providers", "options"],
    path: "/settings/llm-providers",
    page: 1,
    pageSize: OPTIONS_PAGE_SIZE,
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
    },
  })
}

function reposPath(teamId: string) {
  return `/teams/${teamId}/repos`
}

export function useTeamReposPage(
  teamId: string,
  params: { page: number; q?: string },
) {
  const query = params.q?.trim() ?? ""
  return usePaginatedList<RepoIntegration>({
    queryKey: ["teams", teamId, "repos", query],
    path: reposPath(teamId),
    page: params.page,
    filters: query ? { q: query } : undefined,
    enabled: Boolean(teamId),
  })
}

export function useTeamRepo(teamId: string, repoId: string) {
  return useQuery({
    queryKey: ["teams", teamId, "repos", repoId],
    queryFn: () => api<RepoIntegration>(`${reposPath(teamId)}/${repoId}`),
    enabled: Boolean(teamId) && Boolean(repoId),
  })
}

export function useRepoIntegrations() {
  return usePaginatedList<RepoIntegration>({
    queryKey: ["settings", "repos", "options"],
    path: "/settings/repos",
    page: 1,
    pageSize: OPTIONS_PAGE_SIZE,
  })
}

export function useRepoIntegration(id: string) {
  return useQuery({
    queryKey: ["settings", "repos", id],
    queryFn: () => api<RepoIntegration>(`/settings/repos/${id}`),
    enabled: Boolean(id),
  })
}

export function useLlmProvider(id: string) {
  const query = useLlmProviders()
  return {
    ...query,
    data: query.data?.items.find((provider) => provider.id === id),
  }
}

export function useCreateRepoIntegration(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: RepoIntegrationCreate) =>
      api<RepoIntegration>(reposPath(teamId), {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repos"] })
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repositories"] })
      queryClient.invalidateQueries({ queryKey: ["repositories"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useUpdateRepoIntegration(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: RepoIntegrationUpdate
    }) =>
      api<RepoIntegration>(`${reposPath(teamId)}/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repos"] })
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repositories"] })
      queryClient.invalidateQueries({ queryKey: ["repositories"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useDeleteRepoIntegration(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api<void>(`${reposPath(teamId)}/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repos"] })
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repositories"] })
      queryClient.invalidateQueries({ queryKey: ["repositories"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}
