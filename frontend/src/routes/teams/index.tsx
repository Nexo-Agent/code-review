import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"

import { AppShell } from "@/components/layout/AppShell"
import { EmptyState } from "@/components/patterns/empty-state"
import { PaginatedListPanel } from "@/components/patterns/paginated-list-panel"
import { TeamCreateDialog } from "@/components/teams/TeamCreateDialog"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useOrgPermission } from "@/hooks/use-permission"
import { useTeamsPage } from "@/hooks/use-teams"
import { parsePageSearch } from "@/lib/pagination"

export const Route = createFileRoute("/teams/")({
  validateSearch: parsePageSearch,
  component: TeamsPage,
})

function TeamsPage() {
  const navigate = Route.useNavigate()
  const { page } = Route.useSearch()
  const teams = useTeamsPage({ page })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogSession, setDialogSession] = useState(0)

  const canCreateTeam = useOrgPermission("team.create")
  const total = teams.data?.total ?? 0

  function openCreateDialog() {
    setDialogSession((session) => session + 1)
    setDialogOpen(true)
  }

  function goToPage(nextPage: number) {
    void navigate({ search: { page: nextPage, q: "" } })
  }

  return (
    <AppShell
      title="Teams"
      description={`${total} team${total === 1 ? "" : "s"}`}
      actions={
        canCreateTeam ? (
          <Button type="button" size="sm" onClick={openCreateDialog}>
            Create team
          </Button>
        ) : undefined
      }
    >
      {canCreateTeam ? (
        <TeamCreateDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          sessionKey={dialogSession}
        />
      ) : null}
      <PaginatedListPanel query={teams} page={page} onPageChange={goToPage}>
        {(teamList) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Team name</TableHead>
                <TableHead className="text-right">Members</TableHead>
                <TableHead className="text-right">Repos</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {teamList.length ? (
                teamList.map((team) => (
                  <TableRow key={team.id}>
                    <TableCell>
                      <Link
                        to="/teams/$teamId"
                        params={{ teamId: team.id }}
                        className="font-medium hover:underline"
                      >
                        {team.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {team.member_count}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {team.repo_count}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <EmptyState colSpan={3}>
                  {canCreateTeam
                    ? 'No teams yet. Click "Create team" to get started.'
                    : "No teams yet. Contact your org admin."}
                </EmptyState>
              )}
            </TableBody>
          </Table>
        )}
      </PaginatedListPanel>
    </AppShell>
  )
}
