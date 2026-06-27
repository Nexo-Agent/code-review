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

function reposPath(teamId: string, projectId: string) {
  return `/teams/${teamId}/projects/${projectId}/repos`
}

export function useProjectRepos(teamId: string, projectId: string) {
  return useQuery({
    queryKey: ["teams", teamId, "projects", projectId, "repos"],
    queryFn: () => api<RepoIntegration[]>(reposPath(teamId, projectId)),
    enabled: Boolean(teamId) && Boolean(projectId),
  })
}

export function useProjectRepo(
  teamId: string,
  projectId: string,
  repoId: string,
) {
  const query = useProjectRepos(teamId, projectId)
  return {
    ...query,
    data: query.data?.find((repo) => repo.id === repoId),
  }
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

export function useCreateRepoIntegration(teamId: string, projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: RepoIntegrationCreate) =>
      api<RepoIntegration>(reposPath(teamId, projectId), {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["teams", teamId, "projects", projectId, "repos"],
      })
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repositories"] })
      queryClient.invalidateQueries({ queryKey: ["repositories"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useUpdateRepoIntegration(teamId: string, projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: RepoIntegrationUpdate
    }) =>
      api<RepoIntegration>(`${reposPath(teamId, projectId)}/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["teams", teamId, "projects", projectId, "repos"],
      })
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repositories"] })
      queryClient.invalidateQueries({ queryKey: ["repositories"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}

export function useDeleteRepoIntegration(teamId: string, projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api<void>(`${reposPath(teamId, projectId)}/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["teams", teamId, "projects", projectId, "repos"],
      })
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repositories"] })
      queryClient.invalidateQueries({ queryKey: ["repositories"] })
      queryClient.invalidateQueries({ queryKey: ["settings", "repos"] })
    },
  })
}
