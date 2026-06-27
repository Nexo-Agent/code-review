import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { RepoIntegrationDialog } from "@/components/settings/RepoIntegrationDialog"
import { DataPanel } from "@/components/patterns/data-panel"
import { EmptyState } from "@/components/patterns/empty-state"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useProject } from "@/hooks/use-teams"
import { useProjectRepos, useUpdateRepoIntegration } from "@/hooks/use-settings"

export const Route = createFileRoute("/teams/$teamId/projects/$projectId/")({
  component: ProjectDetailPage,
})

function ProjectDetailPage() {
  const { teamId, projectId } = Route.useParams()
  const project = useProject(teamId, projectId)
  const repos = useProjectRepos(teamId, projectId)
  const updateRepo = useUpdateRepoIntegration(teamId, projectId)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogSession, setDialogSession] = useState(0)

  const repoList = repos.data ?? []

  function openCreate() {
    setDialogSession((session) => session + 1)
    setDialogOpen(true)
  }

  async function toggleEnabled(repoId: string, enabled: boolean) {
    try {
      await updateRepo.mutateAsync({ id: repoId, payload: { enabled } })
      toast.success(enabled ? "Repository enabled" : "Repository disabled")
    } catch {
      toast.error("Failed to update repository")
    }
  }

  return (
    <AppShell
      title={project.data?.name ?? "Project"}
      description="Repositories in this project"
      actions={
        <Button type="button" size="sm" onClick={openCreate}>
          Add repository
        </Button>
      }
    >
      <DataPanel loading={project.isPending || repos.isPending} error={project.isError || repos.isError}>
        <RepoIntegrationDialog
          teamId={teamId}
          projectId={projectId}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          repo={null}
          sessionKey={dialogSession}
        />

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Repository</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead>LLM</TableHead>
              <TableHead className="w-20 text-right">Enabled</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {repoList.length ? (
              repoList.map((repo) => (
                <TableRow key={repo.id}>
                  <TableCell>
                    <Link
                      to="/teams/$teamId/projects/$projectId/repos/$repoId"
                      params={{ teamId, projectId, repoId: repo.id }}
                      className="font-medium hover:underline"
                    >
                      {repo.repo_full_name || repo.name || "All repositories"}
                    </Link>
                  </TableCell>
                  <TableCell>{repo.git_provider}</TableCell>
                  <TableCell>{repo.llm_provider_name ?? "Org default"}</TableCell>
                  <TableCell className="text-right">
                    <Switch
                      checked={repo.enabled}
                      onCheckedChange={(enabled) => toggleEnabled(repo.id, enabled)}
                    />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <EmptyState colSpan={4}>
                No repositories yet. Click &quot;Add repository&quot; to get started.
              </EmptyState>
            )}
          </TableBody>
        </Table>
      </DataPanel>
    </AppShell>
  )
}
