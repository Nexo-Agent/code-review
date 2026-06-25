import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { Field } from "@/components/forms/Field"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  useCreateRepoIntegration,
  useDeleteRepoIntegration,
  useLlmProviders,
  useRepoIntegrations,
} from "@/hooks/use-settings"
import {
  emptyRepoForm,
  GIT_PROVIDER_OPTIONS,
} from "@/lib/settings-constants"

export const Route = createFileRoute("/repositories/")({
  component: RepositoriesPage,
})

function RepositoriesPage() {
  const repos = useRepoIntegrations()
  const llmProviders = useLlmProviders()
  const createRepo = useCreateRepoIntegration()
  const deleteRepo = useDeleteRepoIntegration()

  const [showAddForm, setShowAddForm] = useState(false)
  const [newRepo, setNewRepo] = useState(emptyRepoForm)
  const [webhookSecret, setWebhookSecret] = useState("")
  const [githubToken, setGithubToken] = useState("")

  const llmList = llmProviders.data ?? []
  const repoList = repos.data ?? []
  const loading = repos.isPending || llmProviders.isPending

  async function handleCreateRepo(event: React.FormEvent) {
    event.preventDefault()
    try {
      const payload = { ...newRepo }
      if (webhookSecret) payload.github_webhook_secret = webhookSecret
      if (githubToken) payload.github_token = githubToken
      await createRepo.mutateAsync(payload)
      setNewRepo(emptyRepoForm())
      setWebhookSecret("")
      setGithubToken("")
      setShowAddForm(false)
      toast.success("Repository created")
    } catch {
      toast.error("Failed to create repository")
    }
  }

  return (
    <AppShell
      title="Repositories"
      description={`${repoList.length} integration${repoList.length === 1 ? "" : "s"} · Webhook POST /api/v1/webhooks/github`}
      actions={
        <Button
          type="button"
          size="sm"
          variant={showAddForm ? "outline" : "default"}
          onClick={() => setShowAddForm((v) => !v)}
        >
          {showAddForm ? "Cancel" : "Add repository"}
        </Button>
      }
    >
      {showAddForm ? (
        <Card className="mb-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Add repository</CardTitle>
            <CardDescription>
              Map a GitHub repo to webhook credentials and an optional LLM
              provider.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="flex flex-col gap-3" onSubmit={handleCreateRepo}>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Display name">
                  <Input
                    value={newRepo.name ?? ""}
                    onChange={(e) =>
                      setNewRepo({ ...newRepo, name: e.target.value })
                    }
                  />
                </Field>
                <Field label="Repository (owner/repo)">
                  <Input
                    placeholder="empty = all repositories"
                    value={newRepo.repo_full_name ?? ""}
                    onChange={(e) =>
                      setNewRepo({
                        ...newRepo,
                        repo_full_name: e.target.value,
                      })
                    }
                  />
                </Field>
                <Field label="Git provider">
                  <Select
                    value={newRepo.git_provider ?? "github"}
                    onChange={(e) =>
                      setNewRepo({ ...newRepo, git_provider: e.target.value })
                    }
                  >
                    {GIT_PROVIDER_OPTIONS.map((option) => (
                      <option
                        key={option.value}
                        value={option.value}
                        disabled={"disabled" in option && option.disabled}
                      >
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="LLM provider">
                  <Select
                    value={newRepo.llm_provider_id ?? ""}
                    onChange={(e) =>
                      setNewRepo({
                        ...newRepo,
                        llm_provider_id: e.target.value || null,
                      })
                    }
                  >
                    <option value="">Default LLM</option>
                    {llmList.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Webhook secret">
                  <Input
                    type="password"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                  />
                </Field>
                <Field label="GitHub token">
                  <Input
                    type="password"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                  />
                </Field>
              </div>
              <div>
                <Button type="submit" size="sm" disabled={createRepo.isPending}>
                  Create repository
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <div className="rounded-lg border">
        {loading ? (
          <div className="flex flex-col gap-1.5 p-3">
            <Skeleton className="h-7 w-full" />
            <Skeleton className="h-7 w-full" />
          </div>
        ) : repos.isError ? (
          <p className="text-destructive p-3 text-sm">
            Could not load repositories. Run{" "}
            <code className="text-xs">make dev</code> first.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Repository</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>LLM</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-20" />
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
                      {repo.llm_provider_name ?? "Default"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={
                          repo.enabled
                            ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                            : ""
                        }
                      >
                        {repo.enabled ? "Enabled" : "Disabled"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive h-7 px-2"
                        onClick={async () => {
                          if (
                            !confirm(
                              `Delete repository "${repo.repo_full_name || "All repositories"}"?`,
                            )
                          ) {
                            return
                          }
                          try {
                            await deleteRepo.mutateAsync(repo.id)
                            toast.success("Repository deleted")
                          } catch {
                            toast.error("Failed to delete repository")
                          }
                        }}
                      >
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="text-muted-foreground h-12 text-center"
                  >
                    No repositories yet. Click &quot;Add repository&quot; to get
                    started.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </div>
    </AppShell>
  )
}
