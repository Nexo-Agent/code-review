import { redirect } from "@tanstack/react-router"

import type { ActionKey, MeResponse } from "@/api/auth-types"
import { DEFAULT_LIST_SEARCH } from "@/lib/pagination"

export function isOrgAdmin(me: MeResponse | undefined): boolean {
  if (!me) return false
  return (
    me.user.is_org_admin ||
    me.organization_roles?.includes("org_admin") === true
  )
}

export function hasOrgPermission(
  me: MeResponse | undefined,
  action: ActionKey,
): boolean {
  if (!me) return false
  if (me.permissions?.organization.includes(action)) return true
  return isOrgAdmin(me)
}

export function requireOrgPermission(action: ActionKey) {
  return (ctx: { context: unknown }) => {
    const me = (ctx.context as { me?: MeResponse }).me
    if (me && !hasOrgPermission(me, action)) {
      throw redirect({ to: "/teams", search: DEFAULT_LIST_SEARCH })
    }
  }
}

export function hasTeamPermission(
  me: MeResponse | undefined,
  action: ActionKey,
  teamId: string,
): boolean {
  if (!me) return false
  if (hasOrgPermission(me, action)) return true
  return me.permissions?.teams[teamId]?.includes(action) ?? false
}
