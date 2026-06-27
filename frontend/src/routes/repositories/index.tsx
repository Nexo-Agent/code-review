import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { EmptyState } from "@/components/patterns/empty-state"
import { CodeHint } from "@/components/patterns/inline-error"
import { RepoIntegrationDialog } from "@/components/settings/RepoIntegrationDialog"
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
import {
  useLlmProviders,
  useRepoIntegrations,
  useUpdateRepoIntegration,
} from "@/hooks/use-settings"

export const Route = createFileRoute("/repositories/")({
  component: RepositoriesPage,
})

function RepositoriesPage() {
  const repos = useRepoIntegrations()
  const llmProviders = useLlmProviders()
  const updateRepo = useUpdateRepoIntegration()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogSession, setDialogSession] = useState(0)

  const llmList = llmProviders.data ?? []
  const repoList = repos.data ?? []
  const loading = repos.isPending || llmProviders.isPending

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
      title="Repositories"
      actions={
        <Button type="button" size="sm" onClick={openCreate}>
          Add repository
        </Button>
      }
    >
      <RepoIntegrationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        repo={null}
        llmProviders={llmList}
        sessionKey={dialogSession}
      />

      <DataPanel
        loading={loading}
        error={repos.isError}
        errorMessage="Could not load repositories. Run"
        errorHint={<CodeHint>make dev</CodeHint>}
      >
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
                      to="/repositories/$repoId"
                      params={{ repoId: repo.id }}
                      className="font-medium hover:underline"
                    >
                      {repo.repo_full_name || "All repositories"}
                    </Link>
                    {repo.name ? (
                      <p className="text-muted-foreground text-xs">
                        {repo.name}
                      </p>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {repo.git_provider}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {repo.llm_provider_name ?? "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Switch
                      checked={repo.enabled}
                      disabled={updateRepo.isPending}
                      onCheckedChange={(enabled) =>
                        void toggleEnabled(repo.id, enabled)
                      }
                      aria-label={
                        repo.enabled
                          ? `Disable ${repo.repo_full_name || "repository"}`
                          : `Enable ${repo.repo_full_name || "repository"}`
                      }
                    />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <EmptyState colSpan={4}>
                No repositories yet. Click &quot;Add repository&quot; to get
                started.
              </EmptyState>
            )}
          </TableBody>
        </Table>
      </DataPanel>
    </AppShell>
  )
}
