import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import { useMemo, useState } from "react"
import { toast } from "sonner"

import type { RepoIntegration, RepoIntegrationUpdate } from "@/api/settings-types"
import type { Review } from "@/api/types"
import { Field } from "@/components/forms/Field"
import { AppShell } from "@/components/layout/AppShell"
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
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  useDeleteRepoIntegration,
  useLlmProviders,
  useRepoIntegration,
  useUpdateRepoIntegration,
} from "@/hooks/use-settings"
import { useReviews } from "@/hooks/use-reviews"
import { GIT_PROVIDER_OPTIONS } from "@/lib/settings-constants"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/repositories/$repoId")({
  component: RepositoryDetailPage,
})

function statusClass(status: string) {
  switch (status) {
    case "completed":
      return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
    case "failed":
      return "bg-destructive/15 text-destructive"
    case "running":
      return "bg-blue-500/15 text-blue-700 dark:text-blue-400"
    default:
      return "bg-muted text-muted-foreground"
  }
}

function lastRunAt(review: Review): string {
  const ts = review.completed_at ?? review.started_at
  if (!ts) return "—"
  return new Date(ts).toLocaleString()
}

function RepositoryDetailPage() {
  const { repoId } = Route.useParams()
  const navigate = useNavigate()
  const repoQuery = useRepoIntegration(repoId)
  const llmProviders = useLlmProviders()
  const updateRepo = useUpdateRepoIntegration()
  const deleteRepo = useDeleteRepoIntegration()

  const repo = repoQuery.data
  const reviews = useReviews(
    repo?.repo_full_name ? { repo: repo.repo_full_name } : undefined,
  )

  const [draft, setDraft] = useState<RepoIntegration | null>(null)
  const [webhookSecret, setWebhookSecret] = useState("")
  const [githubToken, setGithubToken] = useState("")

  const llmList = llmProviders.data ?? []
  const editing = draft ?? repo

  async function handleSaveSettings() {
    if (!editing) return
    const payload: RepoIntegrationUpdate = {
      name: editing.name,
      git_provider: editing.git_provider,
      repo_full_name: editing.repo_full_name,
      enabled: editing.enabled,
      llm_provider_id: editing.llm_provider_id,
      system_prompt: editing.system_prompt,
    }
    if (webhookSecret) payload.github_webhook_secret = webhookSecret
    if (githubToken) payload.github_token = githubToken
    try {
      await updateRepo.mutateAsync({ id: editing.id, payload })
      setDraft(null)
      setWebhookSecret("")
      setGithubToken("")
      toast.success("Repository settings updated")
    } catch {
      toast.error("Failed to update repository")
    }
  }

  async function handleDelete() {
    if (!repo) return
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
      await navigate({ to: "/repositories" })
    } catch {
      toast.error("Failed to delete repository")
    }
  }

  const reviewColumns = useMemo<ColumnDef<Review>[]>(
    () => [
      {
        accessorKey: "pr_number",
        header: "PR #",
        cell: ({ row }) => (
          <Link
            to="/reviews/$reviewId"
            params={{ reviewId: row.original.id }}
            className="font-medium hover:underline"
          >
            #{row.original.pr_number}
          </Link>
        ),
      },
      {
        accessorKey: "pr_title",
        header: "PR name",
        cell: ({ row }) => {
          const title = row.original.pr_title.trim()
          if (!title) {
            return <span className="text-muted-foreground">—</span>
          }
          return (
            <Link
              to="/reviews/$reviewId"
              params={{ reviewId: row.original.id }}
              className="hover:underline"
              title={title}
            >
              <span className="line-clamp-1">{title}</span>
            </Link>
          )
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge
            variant="secondary"
            className={cn(statusClass(row.original.status))}
          >
            {row.original.status}
          </Badge>
        ),
      },
      {
        accessorKey: "findings_count",
        header: "Findings",
        cell: ({ row }) => {
          const count = row.original.findings_count
          return (
            <span
              className={cn(
                "tabular-nums",
                count === 0 && "text-muted-foreground",
              )}
            >
              {count}
            </span>
          )
        },
      },
      {
        id: "last_run",
        header: "Last run",
        cell: ({ row }) => (
          <span className="text-muted-foreground whitespace-nowrap text-xs">
            {lastRunAt(row.original)}
          </span>
        ),
      },
    ],
    [],
  )

  const reviewTable = useReactTable({
    data: reviews.data?.items ?? [],
    columns: reviewColumns,
    getCoreRowModel: getCoreRowModel(),
  })

  const title = repo
    ? repo.repo_full_name || "All repositories"
    : "Repository"

  return (
    <AppShell
      title={title}
      description={repo?.name || undefined}
      backTo={{ to: "/repositories", label: "Repositories" }}
    >
      {repoQuery.isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : repoQuery.isError || !repo ? (
        <p className="text-destructive text-sm">Repository not found.</p>
      ) : (
        <Tabs defaultValue="reviews" className="gap-3">
          <TabsList className="h-8">
            <TabsTrigger value="reviews" className="px-3 text-xs">
              Reviews
            </TabsTrigger>
            <TabsTrigger value="settings" className="px-3 text-xs">
              Settings
            </TabsTrigger>
          </TabsList>

          <TabsContent value="reviews" className="mt-0">
            <div className="rounded-lg border">
              {reviews.isPending ? (
                <div className="flex flex-col gap-1.5 p-3">
                  <Skeleton className="h-7 w-full" />
                  <Skeleton className="h-7 w-full" />
                </div>
              ) : reviews.isError ? (
                <p className="text-destructive p-3 text-sm">
                  Could not load reviews.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    {reviewTable.getHeaderGroups().map((headerGroup) => (
                      <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <TableHead key={header.id}>
                            {header.isPlaceholder
                              ? null
                              : flexRender(
                                  header.column.columnDef.header,
                                  header.getContext(),
                                )}
                          </TableHead>
                        ))}
                      </TableRow>
                    ))}
                  </TableHeader>
                  <TableBody>
                    {reviewTable.getRowModel().rows.length ? (
                      reviewTable.getRowModel().rows.map((row) => (
                        <TableRow key={row.id}>
                          {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id}>
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext(),
                              )}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell
                          colSpan={reviewColumns.length}
                          className="text-muted-foreground h-12 text-center"
                        >
                          No reviews yet for this repository.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </div>
          </TabsContent>

          <TabsContent value="settings" className="mt-0">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Repository settings</CardTitle>
                <CardDescription>
                  Webhook credentials, LLM mapping, and review prompt.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {editing ? (
                  <div className="flex flex-col gap-3">
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      <Field label="Display name">
                        <Input
                          value={editing.name}
                          onChange={(e) =>
                            setDraft({ ...editing, name: e.target.value })
                          }
                        />
                      </Field>
                      <Field label="Repository (owner/repo)">
                        <Input
                          placeholder="empty = all repositories"
                          value={editing.repo_full_name}
                          onChange={(e) =>
                            setDraft({
                              ...editing,
                              repo_full_name: e.target.value,
                            })
                          }
                        />
                      </Field>
                      <Field label="Git provider">
                        <Select
                          value={editing.git_provider}
                          onChange={(e) =>
                            setDraft({
                              ...editing,
                              git_provider: e.target.value,
                            })
                          }
                        >
                          {GIT_PROVIDER_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </Select>
                      </Field>
                      <Field label="LLM provider">
                        <Select
                          value={editing.llm_provider_id ?? ""}
                          onChange={(e) =>
                            setDraft({
                              ...editing,
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
                      <Field label="Webhook secret (leave blank to keep)">
                        <Input
                          type="password"
                          value={webhookSecret}
                          onChange={(e) => setWebhookSecret(e.target.value)}
                          placeholder={
                            repo.github_webhook_secret_configured
                              ? "Configured"
                              : "Not set"
                          }
                        />
                      </Field>
                      <Field label="GitHub token (leave blank to keep)">
                        <Input
                          type="password"
                          value={githubToken}
                          onChange={(e) => setGithubToken(e.target.value)}
                          placeholder={
                            repo.github_token_configured
                              ? "Configured"
                              : "Not set"
                          }
                        />
                      </Field>
                    </div>
                    <Field label="System prompt">
                      <Textarea
                        rows={6}
                        value={editing.system_prompt}
                        onChange={(e) =>
                          setDraft({
                            ...editing,
                            system_prompt: e.target.value,
                          })
                        }
                        placeholder="Leave empty to use the default code-review prompt"
                      />
                    </Field>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={editing.enabled}
                        onChange={(e) =>
                          setDraft({ ...editing, enabled: e.target.checked })
                        }
                      />
                      Enabled
                    </label>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={handleSaveSettings}
                        disabled={updateRepo.isPending}
                      >
                        Save changes
                      </Button>
                      {draft ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setDraft(null)
                            setWebhookSecret("")
                            setGithubToken("")
                          }}
                        >
                          Reset
                        </Button>
                      ) : null}
                      <Button
                        type="button"
                        size="sm"
                        variant="destructive"
                        onClick={handleDelete}
                        disabled={deleteRepo.isPending}
                      >
                        Delete repository
                      </Button>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </AppShell>
  )
}
