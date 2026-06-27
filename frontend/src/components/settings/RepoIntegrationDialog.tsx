import { ArrowLeft, Copy } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { apiBaseUrl } from "@/api/client"
import type {
  RepoIntegration,
  RepoIntegrationCreate,
  RepoIntegrationUpdate,
} from "@/api/settings-types"
import { Field } from "@/components/forms/Field"
import { ConfirmDialog } from "@/components/patterns/confirm-dialog"
import { ProviderPicker } from "@/components/settings/repo-integration/ProviderPicker"
import {
  getGitProvider,
  getGitProviderForValue,
  GIT_PROVIDER_OPTIONS,
  repoFormFromGitProvider,
  type GitProviderDefinition,
  type GitProviderId,
} from "@/components/settings/repo-integration/providers"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
  useCreateRepoIntegration,
  useDeleteRepoIntegration,
  useLlmProviders,
  useUpdateRepoIntegration,
} from "@/hooks/use-settings"
import { emptyRepoForm } from "@/lib/settings-constants"
import { cn } from "@/lib/utils"

type RepoIntegrationDialogProps = {
  teamId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  repo?: RepoIntegration | null
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
    llm_provider_id: repo.llm_provider_id,
  }
}

function deriveRepoName(repoFullName: string): string {
  const segment = repoFullName.split("/").filter(Boolean).at(-1)
  return segment ?? repoFullName
}

function RepoIntegrationForm({
  teamId,
  repo,
  preset,
  onOpenChange,
  onBack,
  onDeleted,
}: {
  teamId: string
  repo?: RepoIntegration | null
  preset?: GitProviderDefinition
  onOpenChange: (open: boolean) => void
  onBack?: () => void
  onDeleted?: () => void
}) {
  const isEdit = Boolean(repo)
  const hideProviderSelect = !isEdit && Boolean(preset)
  const hideDisplayName = hideProviderSelect
  const llmProviders = useLlmProviders()
  const createRepo = useCreateRepoIntegration(teamId)
  const updateRepo = useUpdateRepoIntegration(teamId)
  const deleteRepo = useDeleteRepoIntegration(teamId)
  const enabledLlmProviders = (llmProviders.data?.items ?? []).filter(
    (provider) => provider.enabled,
  )

  const [form, setForm] = useState(() =>
    preset ? repoFormFromGitProvider(preset) : repoFormFromIntegration(repo),
  )
  const [llmProviderId, setLlmProviderId] = useState(
    () => repo?.llm_provider_id ?? "__default__",
  )
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [webhookSecret, setWebhookSecret] = useState("")
  const [githubToken, setGithubToken] = useState("")
  const [adoPat, setAdoPat] = useState("")
  const [adoWebhookUsername, setAdoWebhookUsername] = useState("")
  const [adoWebhookPassword, setAdoWebhookPassword] = useState("")
  const [systemPrompt, setSystemPrompt] = useState(() => repo?.system_prompt ?? "")

  const editPreset =
    isEdit && repo ? getGitProviderForValue(repo.git_provider) : undefined
  const displayPreset = preset ?? editPreset
  const isAzureDevOps = form.git_provider === "azure-devops"

  const isPending =
    createRepo.isPending || updateRepo.isPending || deleteRepo.isPending

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const repoFullName = form.repo_full_name?.trim() ?? ""
    try {
      if (isEdit && repo) {
        const payload: RepoIntegrationUpdate = {
          name: form.name,
          git_provider: form.git_provider,
          repo_full_name: repoFullName,
          system_prompt: systemPrompt,
          clear_llm_provider_id: llmProviderId === "__default__",
        }
        if (llmProviderId !== "__default__") {
          payload.llm_provider_id = llmProviderId
        }
        if (isAzureDevOps) {
          if (adoPat) payload.ado_pat = adoPat
          if (adoWebhookUsername) {
            payload.ado_webhook_username = adoWebhookUsername
          }
          if (adoWebhookPassword) payload.ado_webhook_password = adoWebhookPassword
        } else {
          if (webhookSecret) payload.github_webhook_secret = webhookSecret
          if (githubToken) payload.github_token = githubToken
        }
        await updateRepo.mutateAsync({ id: repo.id, payload })
        toast.success("Repository updated")
      } else {
        const repoFullName = form.repo_full_name?.trim() ?? ""
        const payload: RepoIntegrationCreate = {
          ...form,
          name: form.name?.trim() || deriveRepoName(repoFullName),
          repo_full_name: repoFullName,
          system_prompt: systemPrompt,
          enabled: true,
          llm_provider_id:
            llmProviderId === "__default__" ? null : llmProviderId,
        }
        if (isAzureDevOps) {
          payload.ado_pat = adoPat
          payload.ado_webhook_username = adoWebhookUsername
          payload.ado_webhook_password = adoWebhookPassword
        } else {
          payload.github_webhook_secret = webhookSecret
          payload.github_token = githubToken
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

  async function confirmDelete() {
    if (!repo) return
    try {
      await deleteRepo.mutateAsync(repo.id)
      toast.success("Repository deleted")
      setDeleteConfirmOpen(false)
      onOpenChange(false)
      onDeleted?.()
    } catch {
      toast.error("Failed to delete repository")
    }
  }

  const formTitle = isEdit
    ? "Edit repository"
    : preset
      ? `Configure ${preset.label}`
      : "Add repository"

  const formDescription = isEdit
    ? "Git credentials, LLM provider, and review prompt for this repository."
    : preset
      ? preset.description
      : "Connect a repository for automated code reviews."

  const repoLabel =
    displayPreset?.repoLabel ??
    (isAzureDevOps ? "Repository (org/project/repo)" : "Repository (owner/repo)")

  const repoPlaceholder =
    displayPreset?.repoPlaceholder ??
    (isAzureDevOps ? "contoso/engineering/web-app" : "acme-corp/backend-api")

  const webhookUrl =
    isEdit && repo?.webhook_url
      ? `${apiBaseUrl()}${repo.webhook_url}`
      : null

  return (
    <>
      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Delete repository?"
        description={`Delete repository "${repo?.repo_full_name || "All repositories"}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteRepo.isPending}
        onConfirm={confirmDelete}
      />
      <DialogHeader className="shrink-0 border-b px-6 py-4">
        <DialogTitle>{formTitle}</DialogTitle>
        <DialogDescription>{formDescription}</DialogDescription>
      </DialogHeader>

      <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit}>
        <div className="flex flex-col gap-3 overflow-y-auto px-6 py-4">
          {!hideDisplayName ? (
            <Field label="Display name">
              <Input
                value={form.name ?? ""}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </Field>
          ) : null}

          {!hideProviderSelect ? (
            <Field label="Git provider">
              <Select
                value={form.git_provider ?? "github"}
                onValueChange={(value) =>
                  setForm({ ...form, git_provider: value })
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select git provider" />
                </SelectTrigger>
                <SelectContent position="popper">
                  <SelectGroup>
                    {GIT_PROVIDER_OPTIONS.map((option) => (
                      <SelectItem
                        key={option.value}
                        value={option.value}
                        disabled={"disabled" in option && option.disabled}
                      >
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
          ) : null}

          <Field label={repoLabel}>
            <Input
              required
              value={form.repo_full_name ?? ""}
              onChange={(e) =>
                setForm({ ...form, repo_full_name: e.target.value })
              }
              placeholder={repoPlaceholder}
            />
          </Field>

          <Field label="LLM provider (from org pool)">
            <Select value={llmProviderId} onValueChange={setLlmProviderId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Org default" />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectGroup>
                  <SelectItem value="__default__">Org default</SelectItem>
                  {enabledLlmProviders.map((provider) => (
                    <SelectItem key={provider.id} value={provider.id}>
                      {provider.name}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>

          {isAzureDevOps ? (
            <>
              <Field
                label={
                  isEdit ? "PAT (leave blank to keep)" : "Personal Access Token"
                }
              >
                <Input
                  type="password"
                  required={!isEdit}
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
                  required={!isEdit}
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
                  required={!isEdit}
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
                  isEdit ? "GitHub token (leave blank to keep)" : "GitHub token"
                }
              >
                <Input
                  type="password"
                  required={!isEdit}
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
              <Field
                label={
                  isEdit
                    ? "Webhook secret (leave blank to keep)"
                    : "Webhook secret"
                }
              >
                <Input
                  type="password"
                  required={!isEdit}
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
            </>
          )}

          {webhookUrl ? (
            <Field label="Webhook URL">
              <div className="flex items-center gap-2">
                <Input readOnly value={webhookUrl} className="font-mono text-xs" />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="shrink-0"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(webhookUrl)
                      toast.success("Webhook URL copied")
                    } catch {
                      toast.error("Could not copy webhook URL")
                    }
                  }}
                >
                  <Copy className="size-4" />
                </Button>
              </div>
            </Field>
          ) : null}

          {isEdit ? (
            <Field label="System prompt">
              <Textarea
                rows={4}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Leave empty to use the default cogito-review prompt"
              />
            </Field>
          ) : null}
        </div>

        <DialogFooter className="w-full shrink-0 flex-row items-center justify-between gap-2 border-t px-6 py-4 sm:justify-between">
          <div className="flex items-center gap-2">
            {isEdit ? (
              <Button
                type="button"
                variant="destructive"
                disabled={isPending}
                onClick={() => setDeleteConfirmOpen(true)}
              >
                Delete
              </Button>
            ) : null}
            {onBack ? (
              <Button
                type="button"
                variant="ghost"
                disabled={isPending}
                onClick={onBack}
              >
                <ArrowLeft data-icon="inline-start" />
                Back
              </Button>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
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
          </div>
        </DialogFooter>
      </form>
    </>
  )
}

function RepoIntegrationCreateFlow({
  teamId,
  sessionKey,
  onOpenChange,
  onDeleted,
  onStepChange,
}: {
  teamId: string
  sessionKey: number
  onOpenChange: (open: boolean) => void
  onDeleted?: () => void
  onStepChange?: (onPicker: boolean) => void
}) {
  const [selectedProviderId, setSelectedProviderId] =
    useState<GitProviderId | null>(null)

  const preset = selectedProviderId
    ? getGitProvider(selectedProviderId)
    : undefined

  function selectProvider(providerId: GitProviderId) {
    setSelectedProviderId(providerId)
    onStepChange?.(false)
  }

  function goBackToPicker() {
    setSelectedProviderId(null)
    onStepChange?.(true)
  }

  if (selectedProviderId && preset) {
    return (
      <RepoIntegrationForm
        key={`create-${selectedProviderId}-${sessionKey}`}
        teamId={teamId}
        preset={preset}
        onOpenChange={onOpenChange}
        onBack={goBackToPicker}
        onDeleted={onDeleted}
      />
    )
  }

  return (
    <>
      <DialogHeader className="shrink-0 border-b px-6 py-4">
        <DialogTitle>Add repository</DialogTitle>
        <DialogDescription>
          Choose a Git provider to connect a repository for code reviews.
        </DialogDescription>
      </DialogHeader>
      <ProviderPicker
        key={sessionKey}
        onSelect={selectProvider}
      />
    </>
  )
}

function RepoIntegrationCreateDialogContent({
  teamId,
  sessionKey,
  onOpenChange,
  onDeleted,
}: {
  teamId: string
  sessionKey: number
  onOpenChange: (open: boolean) => void
  onDeleted?: () => void
}) {
  const [onPicker, setOnPicker] = useState(true)

  return (
    <DialogContent
      className={cn(
        "flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0",
        onPicker
          ? "w-fit max-w-[calc(100%-2rem)] sm:max-w-fit"
          : "sm:max-w-xl",
      )}
    >
      <RepoIntegrationCreateFlow
        teamId={teamId}
        sessionKey={sessionKey}
        onOpenChange={onOpenChange}
        onDeleted={onDeleted}
        onStepChange={setOnPicker}
      />
    </DialogContent>
  )
}

export function RepoIntegrationDialog({
  teamId,
  open,
  onOpenChange,
  repo,
  sessionKey,
  onDeleted,
}: RepoIntegrationDialogProps) {
  const isEdit = Boolean(repo)
  const formKey = `${repo?.id ?? "create"}-${sessionKey}`

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open ? (
        isEdit ? (
          <DialogContent className="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-xl">
            <RepoIntegrationForm
              key={formKey}
              teamId={teamId}
              repo={repo}
              onOpenChange={onOpenChange}
              onDeleted={onDeleted}
            />
          </DialogContent>
        ) : (
          <RepoIntegrationCreateDialogContent
            key={sessionKey}
            teamId={teamId}
            sessionKey={sessionKey}
            onOpenChange={onOpenChange}
            onDeleted={onDeleted}
          />
        )
      ) : null}
    </Dialog>
  )
}
