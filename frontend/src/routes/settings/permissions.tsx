import { createFileRoute, redirect } from "@tanstack/react-router"
import { toast } from "sonner"

import type { MeResponse } from "@/api/auth-types"
import { AppShell } from "@/components/layout/AppShell"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  useRbacCatalog,
  useRbacPermissions,
  useUpdateRbacPermissions,
  type RolePermissionEntry,
} from "@/hooks/use-rbac"
import { hasOrgPermission } from "@/lib/permissions"
import { DEFAULT_LIST_SEARCH } from "@/lib/pagination"

export const Route = createFileRoute("/settings/permissions")({
  beforeLoad: ({ context }) => {
    const me = (context as { me?: MeResponse }).me
    if (me && !hasOrgPermission(me, "settings.rbac.read")) {
      throw redirect({ to: "/teams", search: DEFAULT_LIST_SEARCH })
    }
  },
  component: PermissionsSettingsPage,
})

function PermissionsSettingsPage() {
  const catalog = useRbacCatalog()
  const matrix = useRbacPermissions()
  const update = useUpdateRbacPermissions()

  const teamRoles =
    catalog.data?.roles.filter((r) => r.scope_kind === "team") ?? []
  const teamScopeActions =
    catalog.data?.actions.filter((action) => {
      const entry = matrix.data?.items.find(
        (item) => item.action_key === action.key && item.scope_key === "team",
      )
      return entry !== undefined
    }) ?? []

  function isAllowed(roleKey: string, actionKey: string): boolean {
    return (
      matrix.data?.items.find(
        (item) =>
          item.role_key === roleKey &&
          item.action_key === actionKey &&
          item.scope_key === "team",
      )?.allowed ?? false
    )
  }

  async function togglePermission(
    roleKey: string,
    actionKey: string,
    allowed: boolean,
  ) {
    const entry: RolePermissionEntry = {
      role_key: roleKey,
      action_key: actionKey,
      scope_key: "team",
      allowed,
    }
    try {
      await update.mutateAsync([entry])
      toast.success("Permission updated")
    } catch {
      toast.error("Could not update permission")
    }
  }

  return (
    <AppShell
      title="Permissions"
      description="Configure which team roles may perform each action. Organization admin permissions are fixed."
    >
      {catalog.isPending || matrix.isPending ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-48">Action</TableHead>
                {teamRoles.map((role) => (
                  <TableHead key={role.key} className="text-center">
                    {role.display_name}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {teamScopeActions.map((action) => (
                <TableRow key={action.key}>
                  <TableCell className="font-mono text-xs">
                    {action.key}
                  </TableCell>
                  {teamRoles.map((role) => (
                    <TableCell key={role.key} className="text-center">
                      <Checkbox
                        checked={isAllowed(role.key, action.key)}
                        disabled={update.isPending || role.key === "org_admin"}
                        onCheckedChange={(checked) =>
                          void togglePermission(
                            role.key,
                            action.key,
                            checked === true,
                          )
                        }
                      />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </AppShell>
  )
}
