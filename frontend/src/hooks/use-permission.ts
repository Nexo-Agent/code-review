import { useMe } from "@/hooks/use-auth"
import type { ActionKey } from "@/api/auth-types"

export function usePermission(action: ActionKey, teamId?: string): boolean {
  const me = useMe()
  const permissions = me.data?.permissions

  if (!permissions) {
    return me.data?.user.is_org_admin ?? false
  }

  if (permissions.organization.includes(action)) {
    return true
  }

  if (teamId) {
    return permissions.teams[teamId]?.includes(action) ?? false
  }

  return Object.values(permissions.teams).some((actions) =>
    actions.includes(action),
  )
}

export function useOrgPermission(action: ActionKey): boolean {
  return usePermission(action)
}
