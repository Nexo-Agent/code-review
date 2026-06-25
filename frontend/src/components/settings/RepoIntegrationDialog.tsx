import { useState } from "react"
import { toast } from "sonner"

import type {
  LlmProvider,
  RepoIntegration,
  RepoIntegrationCreate,
  RepoIntegrationUpdate,
} from "@/api/settings-types"
import { Field } from "@/components/forms/Field"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
  useCreateRepoIntegration,
  useDeleteRepoIntegration,
  useUpdateRepoIntegration,
} from "@/hooks/use-settings"
import { emptyRepoForm, GIT_PROVIDER_OPTIONS } from "@/lib/settings-constants"

type RepoIntegrationDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  repo?: RepoIntegration | null
  llmProviders: LlmProvider[]
  sessionKey: number
  onDeleted?: () => void
}

function repoFormFromIntegration(
  repo: RepoIntegration | null | undefined,
): RepoIntegrationCreate {
  if (!repo) return emptyRepoForm()
  return {
    name: repo.name,
    git_provider: repo.git_provider,
    repo_full_name: repo.repo_full_name,
    ado_organization: repo.ado_organization,
    ado_project: repo.ado_project,
    llm_provider_id: repo.llm_provider_id,
    enabled: repo.enabled,
  }
}

function RepoIntegrationForm({
  repo,
  llmProviders,
  onOpenChange,
  onDeleted,
}: {
  repo?: RepoIntegration | null
  llmProviders: LlmProvider[]
  onOpenChange: (open: boolean) => void
  onDeleted?: () => void
}) {
  const isEdit = Boolean(repo)
  const createRepo = useCreateRepoIntegration()
  const updateRepo = useUpdateRepoIntegration()
  const deleteRepo = useDeleteRepoIntegration()

  const [form, setForm] = useState(() => repoFormFromIntegration(repo))
  const [webhookSecret, setWebhookSecret] = useState("")
  const [githubToken, setGithubToken] = useState("")
  const [adoPat, setAdoPat] = useState("")
  const [adoWebhookUsername, setAdoWebhookUsername] = useState("")
  const [adoWebhookPassword, setAdoWebhookPassword] = useState("")
  const [systemPrompt, setSystemPrompt] = useState(() => repo?.system_prompt ?? "")

  const isAzureDevOps = form.git_provider === "azure-devops"
  const isPending =
    createRepo.isPending || updateRepo.isPending || deleteRepo.isPending

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    try {
      if (isEdit && repo) {
        const payload: RepoIntegrationUpdate = {
          name: form.name,
          git_provider: form.git_provider,
          repo_full_name: form.repo_full_name,
          llm_provider_id: form.llm_provider_id,
          enabled: form.enabled,
          system_prompt: systemPrompt,
        }
        if (isAzureDevOps) {
          payload.ado_organization = form.ado_organization
          payload.ado_project = form.ado_project
          if (adoPat) payload.ado_pat = adoPat
          if (adoWebhookUsername) payload.ado_webhook_username = adoWebhookUsername
          if (adoWebhookPassword) payload.ado_webhook_password = adoWebhookPassword
        } else {
          if (webhookSecret) payload.github_webhook_secret = webhookSecret
          if (githubToken) payload.github_token = githubToken
        }
        await updateRepo.mutateAsync({ id: repo.id, payload })
        toast.success("Repository updated")
      } else {
        const payload = { ...form, system_prompt: systemPrompt }
        if (isAzureDevOps) {
          if (adoPat) payload.ado_pat = adoPat
          if (adoWebhookUsername) payload.ado_webhook_username = adoWebhookUsername
          if (adoWebhookPassword) payload.ado_webhook_password = adoWebhookPassword
        } else {
          if (webhookSecret) payload.github_webhook_secret = webhookSecret
          if (githubToken) payload.github_token = githubToken
        }
        await createRepo.mutateAsync(payload)
        toast.success("Repository created")
      }
      onOpenChange(false)
    } catch {
      toast.error(
        isEdit ? "Failed to update repository" : "Failed to create repository",
      )
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
      onOpenChange(false)
      onDeleted?.()
    } catch {
      toast.error("Failed to delete repository")
    }
  }

  return (
    <>
      <DialogHeader className="shrink-0 border-b px-6 py-4">
        <DialogTitle>
          {isEdit ? "Edit repository" : "Add repository"}
        </DialogTitle>
        <DialogDescription>
          {isEdit
            ? "Webhook credentials, LLM mapping, and review prompt."
            : "Map a repository to webhook credentials and an optional LLM provider."}
        </DialogDescription>
      </DialogHeader>

      <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit}>
        <div className="flex flex-col gap-3 overflow-y-auto px-6 py-4">
          <Field label="Display name">
            <Input
              value={form.name ?? ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Field>
          <Field label="Git provider">
            <Select
              value={form.git_provider ?? "github"}
              onChange={(e) =>
                setForm({ ...form, git_provider: e.target.value })
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
          <Field
            label={
              isAzureDevOps
                ? "Repository (org/project/repo)"
                : "Repository (owner/repo)"
            }
          >
            <Input
              placeholder={
                isAzureDevOps
                  ? "fabrikam/MyProject/MyRepo — empty = all repositories"
                  : "empty = all repositories"
              }
              value={form.repo_full_name ?? ""}
              onChange={(e) =>
                setForm({ ...form, repo_full_name: e.target.value })
              }
            />
          </Field>
          {isAzureDevOps ? (
            <>
              <Field label="Organization">
                <Input
                  value={form.ado_organization ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, ado_organization: e.target.value })
                  }
                  placeholder="fabrikam"
                />
              </Field>
              <Field label="Project">
                <Input
                  value={form.ado_project ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, ado_project: e.target.value })
                  }
                  placeholder="MyProject"
                />
              </Field>
              <Field
                label={
                  isEdit ? "PAT (leave blank to keep)" : "Personal Access Token"
                }
              >
                <Input
                  type="password"
                  value={adoPat}
                  onChange={(e) => setAdoPat(e.target.value)}
                  placeholder={
                    isEdit
                      ? repo?.ado_pat_configured
                        ? "Configured"
                        : "Not set"
                      : undefined
                  }
                />
              </Field>
              <Field label="Webhook username">
                <Input
                  value={adoWebhookUsername}
                  onChange={(e) => setAdoWebhookUsername(e.target.value)}
                  placeholder={
                    isEdit && repo?.ado_webhook_configured
                      ? "Configured"
                      : "Service hook basic auth username"
                  }
                />
              </Field>
              <Field
                label={
                  isEdit
                    ? "Webhook password (leave blank to keep)"
                    : "Webhook password"
                }
              >
                <Input
                  type="password"
                  value={adoWebhookPassword}
                  onChange={(e) => setAdoWebhookPassword(e.target.value)}
                  placeholder={
                    isEdit
                      ? repo?.ado_webhook_configured
                        ? "Configured"
                        : "Not set"
                      : "Service hook basic auth password"
                  }
                />
              </Field>
            </>
          ) : (
            <>
              <Field
                label={
                  isEdit
                    ? "Webhook secret (leave blank to keep)"
                    : "Webhook secret"
                }
              >
                <Input
                  type="password"
                  value={webhookSecret}
                  onChange={(e) => setWebhookSecret(e.target.value)}
                  placeholder={
                    isEdit
                      ? repo?.github_webhook_secret_configured
                        ? "Configured"
                        : "Not set"
                      : undefined
                  }
                />
              </Field>
              <Field
                label={
                  isEdit ? "GitHub token (leave blank to keep)" : "GitHub token"
                }
              >
                <Input
                  type="password"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder={
                    isEdit
                      ? repo?.github_token_configured
                        ? "Configured"
                        : "Not set"
                      : undefined
                  }
                />
              </Field>
            </>
          )}
          <Field label="LLM provider">
            <Select
              value={form.llm_provider_id ?? ""}
              onChange={(e) =>
                setForm({
                  ...form,
                  llm_provider_id: e.target.value || null,
                })
              }
            >
              <option value="">Default LLM</option>
              {llmProviders.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </Field>
          {isEdit ? (
            <Field label="System prompt">
              <Textarea
                rows={4}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Leave empty to use the default code-review prompt"
              />
            </Field>
          ) : null}
          <div className="flex items-center gap-2">
            <Checkbox
              id="repo-enabled"
              checked={form.enabled ?? true}
              onCheckedChange={(checked) =>
                setForm({ ...form, enabled: checked === true })
              }
            />
            <Label htmlFor="repo-enabled" className="font-normal">
              Enabled
            </Label>
          </div>
        </div>

        <DialogFooter className="shrink-0 border-t px-6 py-4">
          {isEdit ? (
            <Button
              type="button"
              variant="destructive"
              disabled={isPending}
              onClick={handleDelete}
              className="mr-auto"
            >
              Delete
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            disabled={isPending}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isEdit ? "Save changes" : "Create repository"}
          </Button>
        </DialogFooter>
      </form>
    </>
  )
}

export function RepoIntegrationDialog({
  open,
  onOpenChange,
  repo,
  llmProviders,
  sessionKey,
  onDeleted,
}: RepoIntegrationDialogProps) {
  const formKey = `${repo?.id ?? "create"}-${sessionKey}`

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
        {open ? (
          <RepoIntegrationForm
            key={formKey}
            repo={repo}
            llmProviders={llmProviders}
            onOpenChange={onOpenChange}
            onDeleted={onDeleted}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
