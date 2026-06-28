import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/api/client"

export interface RolePermissionEntry {
  role_key: string
  action_key: string
  scope_key: string
  allowed: boolean
}

export interface RolePermissionMatrix {
  items: RolePermissionEntry[]
}

export interface RbacCatalogRole {
  key: string
  display_name: string
  scope_kind: string
  description: string
}

export interface RbacCatalog {
  roles: RbacCatalogRole[]
  actions: { key: string; display_name: string; description: string }[]
  scopes: { key: string; display_name: string; description: string }[]
}

export function useRbacPermissions() {
  return useQuery({
    queryKey: ["rbac", "permissions"],
    queryFn: () => api<RolePermissionMatrix>("/settings/rbac/permissions"),
  })
}

export function useRbacCatalog() {
  return useQuery({
    queryKey: ["rbac", "catalog"],
    queryFn: () => api<RbacCatalog>("/settings/rbac/catalog"),
  })
}

export function useUpdateRbacPermissions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (updates: RolePermissionEntry[]) =>
      api<RolePermissionMatrix>("/settings/rbac/permissions", {
        method: "PUT",
        body: JSON.stringify({ updates }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac", "permissions"] })
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] })
    },
  })
}
