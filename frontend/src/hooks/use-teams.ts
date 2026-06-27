import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/api/client"
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  Team,
  TeamCreate,
  TeamMember,
  TeamMemberCreate,
  TeamRepository,
  OrgMember,
  OrgRepository,
  TeamUpdate,
} from "@/api/team-types"
import type { User } from "@/api/auth-types"

export function useTeams() {
  return useQuery({
    queryKey: ["teams"],
    queryFn: () => api<Team[]>("/teams"),
  })
}

export function useCreateTeam() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TeamCreate) =>
      api<Team>("/teams", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] })
    },
  })
}

export function useUpdateTeam(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TeamUpdate) =>
      api<Team>(`/teams/${teamId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] })
    },
  })
}

export function useDeleteTeam(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>(`/teams/${teamId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] })
    },
  })
}

export function useTeamRepositories(teamId: string) {
  return useQuery({
    queryKey: ["teams", teamId, "repositories"],
    queryFn: () => api<TeamRepository[]>(`/teams/${teamId}/repositories`),
    enabled: Boolean(teamId),
  })
}

export function useOrgRepositories() {
  return useQuery({
    queryKey: ["repositories"],
    queryFn: () => api<OrgRepository[]>("/repositories"),
  })
}

export function useOrgMembers() {
  return useQuery({
    queryKey: ["members"],
    queryFn: () => api<OrgMember[]>("/members"),
  })
}

export function useProjects(teamId: string) {
  return useQuery({
    queryKey: ["teams", teamId, "projects"],
    queryFn: () => api<Project[]>(`/teams/${teamId}/projects`),
    enabled: Boolean(teamId),
  })
}

export function useProject(teamId: string, projectId: string) {
  return useQuery({
    queryKey: ["teams", teamId, "projects", projectId],
    queryFn: () => api<Project>(`/teams/${teamId}/projects/${projectId}`),
    enabled: Boolean(teamId) && Boolean(projectId),
  })
}

export function useCreateProject(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ProjectCreate) =>
      api<Project>(`/teams/${teamId}/projects`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "projects"] })
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "repositories"] })
      queryClient.invalidateQueries({ queryKey: ["teams"] })
    },
  })
}

export function useUpdateProject(teamId: string, projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ProjectUpdate) =>
      api<Project>(`/teams/${teamId}/projects/${projectId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "projects"] })
      queryClient.invalidateQueries({
        queryKey: ["teams", teamId, "projects", projectId],
      })
    },
  })
}

export function useTeamMembers(teamId: string) {
  return useQuery({
    queryKey: ["teams", teamId, "members"],
    queryFn: () => api<TeamMember[]>(`/teams/${teamId}/members`),
    enabled: Boolean(teamId),
  })
}

export function useUsers() {
  return useQuery({
    queryKey: ["auth", "users"],
    queryFn: () => api<User[]>("/auth/users"),
  })
}

export function useAddTeamMember(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TeamMemberCreate) =>
      api<TeamMember>(`/teams/${teamId}/members`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "members"] })
      queryClient.invalidateQueries({ queryKey: ["members"] })
      queryClient.invalidateQueries({ queryKey: ["teams"] })
    },
  })
}

export function useRemoveTeamMember(teamId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      api<void>(`/teams/${teamId}/members/${userId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams", teamId, "members"] })
      queryClient.invalidateQueries({ queryKey: ["members"] })
      queryClient.invalidateQueries({ queryKey: ["teams"] })
    },
  })
}
