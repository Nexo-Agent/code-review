import { createFileRoute } from "@tanstack/react-router"
import { Settings } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import type { TeamMember } from "@/api/team-types"
import { AppShell } from "@/components/layout/AppShell"
import { ConfirmDialog } from "@/components/patterns/confirm-dialog"
import { EmptyState } from "@/components/patterns/empty-state"
import { PaginatedListPanel } from "@/components/patterns/paginated-list-panel"
import {
  TABLE_ACTIONS_CELL_CLASS,
  TABLE_ACTIONS_HEAD_CLASS,
  TableRowActions,
} from "@/components/patterns/table-actions"
import { TeamMemberAddDialog } from "@/components/teams/TeamMemberAddDialog"
import { TeamRepositoryAddDialog } from "@/components/teams/TeamRepositoryAddDialog"
import { TeamSettingsDialog } from "@/components/teams/TeamSettingsDialog"
import {
  RepoIntegrationEnabledCell,
  RepoIntegrationLlmCell,
  RepoIntegrationNameCell,
  RepoIntegrationProviderCell,
} from "@/components/repositories/RepoIntegrationListCells"
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
import { usePermission } from "@/hooks/use-permission"
import {
  useRemoveTeamMember,
  useTeamMembersPage,
  useTeamRepositoriesPage,
  useTeams,
} from "@/hooks/use-teams"

export const Route = createFileRoute("/teams/$teamId/")({
  component: TeamDetailPage,
})

function TeamDetailPage() {
  const { teamId } = Route.useParams()
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

  const canUpdateTeam = usePermission("team.update", teamId)
  const canAddRepo = usePermission("repo.create", teamId)
  const canAddMember = usePermission("team.member.add", teamId)
  const canRemoveMember = usePermission("team.member.remove", teamId)
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
        canUpdateTeam && team ? (
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
      {canUpdateTeam && team ? (
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
          {tab === "repositories" ? (
            canAddRepo ? (
              <Button type="button" size="sm" onClick={openRepositoryDialog}>
                Add repository
              </Button>
            ) : null
          ) : canAddMember ? (
            <Button type="button" size="sm" onClick={openMemberDialog}>
              Add member
            </Button>
          ) : null}
        </div>

        {canAddRepo ? (
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
                    <TableHead>Provider</TableHead>
                    <TableHead>LLM</TableHead>
                    <TableHead className="w-32 text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {repoList.length ? (
                    repoList.map((repo) => (
                      <TableRow key={repo.id}>
                        <TableCell>
                          <RepoIntegrationNameCell repo={repo} teamId={teamId} />
                        </TableCell>
                        <TableCell>
                          <RepoIntegrationProviderCell repo={repo} />
                        </TableCell>
                        <TableCell>
                          <RepoIntegrationLlmCell repo={repo} />
                        </TableCell>
                        <TableCell>
                          <RepoIntegrationEnabledCell repo={repo} />
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <EmptyState colSpan={4}>
                      {canAddRepo
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
          {canAddMember ? (
            <TeamMemberAddDialog
              teamId={teamId}
              open={memberDialogOpen}
              onOpenChange={setMemberDialogOpen}
              sessionKey={memberDialogSession}
            />
          ) : null}
          <TeamMembersTable
            teamId={teamId}
            members={members}
            memberPage={memberPage}
            onMemberPageChange={setMemberPage}
            canAddMember={canAddMember}
            canRemoveMember={canRemoveMember}
          />
        </TabsContent>
      </Tabs>
    </AppShell>
  )
}

const TEAM_ROLE_LABELS: Record<string, string> = {
  team_admin: "Team admin",
  member: "Member",
  viewer: "Viewer",
}

function TeamMembersTable({
  teamId,
  members,
  memberPage,
  onMemberPageChange,
  canAddMember,
  canRemoveMember,
}: {
  teamId: string
  members: ReturnType<typeof useTeamMembersPage>
  memberPage: number
  onMemberPageChange: (page: number) => void
  canAddMember: boolean
  canRemoveMember: boolean
}) {
  const removeMember = useRemoveTeamMember(teamId)
  const [pendingRemove, setPendingRemove] = useState<TeamMember | null>(null)
  const actionColSpan = canRemoveMember ? 3 : 2

  async function handleRemoveConfirm() {
    if (!pendingRemove) return
    try {
      await removeMember.mutateAsync(pendingRemove.user_id)
      toast.success("Member removed")
      setPendingRemove(null)
    } catch {
      toast.error("Failed to remove member")
    }
  }

  return (
    <>
      <PaginatedListPanel
        query={members}
        page={memberPage}
        onPageChange={onMemberPageChange}
      >
        {(memberList) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                {canRemoveMember ? (
                  <TableHead className={TABLE_ACTIONS_HEAD_CLASS}>
                    Actions
                  </TableHead>
                ) : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {memberList.length ? (
                memberList.map((member) => (
                  <TableRow key={member.user_id} className="hover:bg-muted/30">
                    <TableCell className="font-medium">
                      {member.user_email}
                    </TableCell>
                    <TableCell>
                      {TEAM_ROLE_LABELS[member.role] ?? member.role}
                    </TableCell>
                    {canRemoveMember ? (
                      <TableCell className={TABLE_ACTIONS_CELL_CLASS}>
                        <TableRowActions>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-destructive h-8 px-3"
                            onClick={() => setPendingRemove(member)}
                          >
                            Remove
                          </Button>
                        </TableRowActions>
                      </TableCell>
                    ) : null}
                  </TableRow>
                ))
              ) : (
                <EmptyState colSpan={actionColSpan}>
                  {canAddMember
                    ? 'No members yet. Click "Add member" to assign users.'
                    : "No members listed for this team."}
                </EmptyState>
              )}
            </TableBody>
          </Table>
        )}
      </PaginatedListPanel>

      <ConfirmDialog
        open={pendingRemove !== null}
        onOpenChange={(open) => {
          if (!open) setPendingRemove(null)
        }}
        title="Remove team member?"
        description={
          pendingRemove
            ? `Remove ${pendingRemove.user_email} from this team.`
            : ""
        }
        confirmLabel="Remove"
        variant="destructive"
        loading={removeMember.isPending}
        onConfirm={handleRemoveConfirm}
      />
    </>
  )
}
