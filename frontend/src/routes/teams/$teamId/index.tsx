import { createFileRoute, Link } from "@tanstack/react-router"
import { Settings } from "lucide-react"
import { useState } from "react"

import { AppShell } from "@/components/layout/AppShell"
import { EmptyState } from "@/components/patterns/empty-state"
import { PaginatedListPanel } from "@/components/patterns/paginated-list-panel"
import { TeamMemberAddDialog } from "@/components/teams/TeamMemberAddDialog"
import { TeamRepositoryAddDialog } from "@/components/teams/TeamRepositoryAddDialog"
import { TeamSettingsDialog } from "@/components/teams/TeamSettingsDialog"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useMe } from "@/hooks/use-auth"
import {
  useTeamMembersPage,
  useTeamRepositoriesPage,
  useTeams,
} from "@/hooks/use-teams"

export const Route = createFileRoute("/teams/$teamId/")({
  component: TeamDetailPage,
})

function TeamDetailPage() {
  const { teamId } = Route.useParams()
  const me = useMe()
  const teams = useTeams()
  const [tab, setTab] = useState("repositories")
  const [repoPage, setRepoPage] = useState(1)
  const [memberPage, setMemberPage] = useState(1)
  const repositories = useTeamRepositoriesPage(teamId, { page: repoPage })
  const members = useTeamMembersPage(teamId, { page: memberPage })
  const [repositoryDialogOpen, setRepositoryDialogOpen] = useState(false)
  const [repositoryDialogSession, setRepositoryDialogSession] = useState(0)
  const [memberDialogOpen, setMemberDialogOpen] = useState(false)
  const [memberDialogSession, setMemberDialogSession] = useState(0)
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false)
  const [settingsDialogSession, setSettingsDialogSession] = useState(0)

  const isOrgAdmin = me.data?.user.is_org_admin ?? false
  const team = teams.data?.items.find((row) => row.id === teamId)

  function openRepositoryDialog() {
    setRepositoryDialogSession((session) => session + 1)
    setRepositoryDialogOpen(true)
  }

  function openMemberDialog() {
    setMemberDialogSession((session) => session + 1)
    setMemberDialogOpen(true)
  }

  function openSettingsDialog() {
    setSettingsDialogSession((session) => session + 1)
    setSettingsDialogOpen(true)
  }

  return (
    <AppShell
      title={team?.name ?? "Team"}
      actions={
        isOrgAdmin && team ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={openSettingsDialog}
          >
            <Settings className="size-4" />
            Team settings
          </Button>
        ) : null
      }
    >
      {isOrgAdmin && team ? (
        <TeamSettingsDialog
          team={team}
          open={settingsDialogOpen}
          onOpenChange={setSettingsDialogOpen}
          sessionKey={settingsDialogSession}
        />
      ) : null}

      <Tabs value={tab} onValueChange={setTab}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabsList variant="line">
            <TabsTrigger value="repositories">Repositories</TabsTrigger>
            <TabsTrigger value="members">Members</TabsTrigger>
          </TabsList>
          {isOrgAdmin ? (
            tab === "repositories" ? (
              <Button type="button" size="sm" onClick={openRepositoryDialog}>
                Add repository
              </Button>
            ) : (
              <Button type="button" size="sm" onClick={openMemberDialog}>
                Add member
              </Button>
            )
          ) : null}
        </div>

        {isOrgAdmin ? (
          <TeamRepositoryAddDialog
            teamId={teamId}
            open={repositoryDialogOpen}
            onOpenChange={setRepositoryDialogOpen}
            sessionKey={repositoryDialogSession}
          />
        ) : null}

        <TabsContent value="repositories" className="mt-4">
          <PaginatedListPanel
            query={repositories}
            page={repoPage}
            onPageChange={setRepoPage}
          >
            {(repoList) => (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Repository</TableHead>
                    <TableHead>LLM</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {repoList.length ? (
                    repoList.map((repo) => (
                      <TableRow key={repo.id}>
                        <TableCell>
                          <Link
                            to="/teams/$teamId/repos/$repoId"
                            params={{
                              teamId,
                              repoId: repo.id,
                            }}
                            className="font-medium hover:underline"
                          >
                            {repo.repo_full_name || repo.name || "All repositories"}
                          </Link>
                        </TableCell>
                        <TableCell>
                          {repo.llm_provider_name ?? "Org default"}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <EmptyState colSpan={2}>
                      {isOrgAdmin
                        ? 'No repositories yet. Click "Add repository" to connect one.'
                        : "No repositories in this team yet."}
                    </EmptyState>
                  )}
                </TableBody>
              </Table>
            )}
          </PaginatedListPanel>
        </TabsContent>

        <TabsContent value="members" className="mt-4">
          {isOrgAdmin ? (
            <TeamMemberAddDialog
              teamId={teamId}
              open={memberDialogOpen}
              onOpenChange={setMemberDialogOpen}
              sessionKey={memberDialogSession}
            />
          ) : null}
          <PaginatedListPanel
            query={members}
            page={memberPage}
            onPageChange={setMemberPage}
          >
            {(memberList) => (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {memberList.length ? (
                    memberList.map((member) => (
                      <TableRow key={member.user_id}>
                        <TableCell>{member.user_email}</TableCell>
                        <TableCell>{member.role}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <EmptyState colSpan={2}>
                      {isOrgAdmin
                        ? 'No members yet. Click "Add member" to assign users.'
                        : "No members listed for this team."}
                    </EmptyState>
                  )}
                </TableBody>
              </Table>
            )}
          </PaginatedListPanel>
        </TabsContent>
      </Tabs>
    </AppShell>
  )
}
