import { ArrowLeft } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import type { LlmProvider, LlmProviderCreate } from "@/api/settings-types"
import { Field } from "@/components/forms/Field"
import { ProviderLogo } from "@/components/settings/llm-provider/ProviderLogo"
import { ProviderPicker } from "@/components/settings/llm-provider/ProviderPicker"
import {
  getLlmProviderPreset,
  getLlmProviderPresetForProviderId,
  llmFormFromPreset,
  llmProviderIdOptions,
  type LlmProviderPresetDefinition,
  type LlmProviderPresetId,
} from "@/components/settings/llm-provider/providers"
import { ConfirmDialog } from "@/components/patterns/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
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
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  useCreateLlmProvider,
  useDeleteLlmProvider,
  useUpdateLlmProvider,
} from "@/hooks/use-settings"
import { emptyLlmForm } from "@/lib/settings-constants"
import { cn } from "@/lib/utils"

type LlmProviderDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  provider?: LlmProvider | null
  sessionKey: number
  canDelete?: boolean
  onDeleted?: () => void
}

export type LlmProviderFormProps = {
  provider?: LlmProvider | null
  preset?: LlmProviderPresetDefinition
  canDelete?: boolean
  variant?: "dialog" | "page"
  onSaved?: () => void
  onCancel?: () => void
  onBack?: () => void
  onDeleted?: () => void
}

function llmFormFromProvider(
  provider: LlmProvider | null | undefined,
): LlmProviderCreate {
  if (!provider) return emptyLlmForm()
  return {
    name: provider.name,
    provider_id: provider.provider_id,
    base_url: provider.base_url,
    model: provider.model,
    is_default: provider.is_default,
  }
}

export function LlmProviderForm({
  provider,
  preset,
  canDelete,
  variant = "dialog",
  onSaved,
  onCancel,
  onBack,
  onDeleted,
}: LlmProviderFormProps) {
  const isEdit = Boolean(provider)
  const isPage = variant === "page"
  const isMinimalCreate = !isEdit && Boolean(preset)
  const createLlm = useCreateLlmProvider()
  const updateLlm = useUpdateLlmProvider()
  const deleteLlm = useDeleteLlmProvider()

  const [form, setForm] = useState(() =>
    preset ? llmFormFromPreset(preset) : llmFormFromProvider(provider),
  )
  const [apiToken, setApiToken] = useState("")
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  const editPreset =
    isEdit && provider
      ? getLlmProviderPresetForProviderId(provider.provider_id)
      : undefined
  const displayPreset = preset ?? editPreset

  const isPending =
    createLlm.isPending || updateLlm.isPending || deleteLlm.isPending

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    try {
      if (isEdit && provider) {
        await updateLlm.mutateAsync({
          id: provider.id,
          payload: {
            name: form.name,
            provider_id: form.provider_id,
            base_url: form.base_url,
            model: form.model,
            is_default: form.is_default,
            ...(apiToken ? { api_token: apiToken } : {}),
          },
        })
        toast.success("LLM provider updated")
      } else {
        const payload = {
          ...form,
          name: form.name.trim() || preset?.label || form.name,
        }
        if (!payload.api_token) delete payload.api_token
        await createLlm.mutateAsync(payload)
        toast.success("LLM provider created")
      }
      onSaved?.()
    } catch {
      toast.error(
        isEdit ? "Failed to update LLM provider" : "Failed to create LLM provider",
      )
    }
  }

  async function confirmDelete() {
    if (!provider) return
    try {
      await deleteLlm.mutateAsync(provider.id)
      toast.success("LLM provider deleted")
      setDeleteConfirmOpen(false)
      onDeleted?.()
    } catch {
      toast.error("Failed to delete LLM provider")
    }
  }

  const formFields = (
    <>
      {displayPreset && (isMinimalCreate || isPage) ? (
        <div className="flex items-center gap-4 rounded-lg border p-4">
          <ProviderLogo providerId={displayPreset.id} className="size-12" />
          <div className="min-w-0 flex-1">
            <p className="font-medium">{displayPreset.label}</p>
            <p className="text-muted-foreground text-sm">
              {displayPreset.description}
            </p>
          </div>
        </div>
      ) : null}

      {!(isMinimalCreate && displayPreset) ? (
        <Field label="Name">
          <Input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder={displayPreset?.label}
          />
        </Field>
      ) : null}

      {!isMinimalCreate ? (
        <Field label="Provider ID">
          <Select
            value={form.provider_id}
            onValueChange={(value) => setForm({ ...form, provider_id: value })}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectGroup>
                {llmProviderIdOptions(form.provider_id).map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
      ) : null}

      {(!isMinimalCreate || preset?.showBaseUrl) ? (
        <Field label="Base URL">
          <Input
            required
            value={form.base_url}
            onChange={(e) => setForm({ ...form, base_url: e.target.value })}
          />
        </Field>
      ) : null}

      <Field label="Model">
        <Input
          required
          value={form.model}
          onChange={(e) => setForm({ ...form, model: e.target.value })}
          placeholder={displayPreset?.modelPlaceholder ?? "e.g. gpt-4o"}
        />
      </Field>

      <Field label={isEdit ? "API token (leave blank to keep)" : "API token"}>
        <Input
          type="password"
          required={!isEdit}
          value={isEdit ? apiToken : (form.api_token ?? "")}
          onChange={(e) =>
            isEdit
              ? setApiToken(e.target.value)
              : setForm({ ...form, api_token: e.target.value })
          }
          placeholder={
            isEdit
              ? provider?.api_token_configured
                ? "Configured"
                : "Not set"
              : undefined
          }
        />
      </Field>

      <div className="flex items-center gap-2">
        <Checkbox
          id="llm-is-default"
          checked={form.is_default ?? false}
          onCheckedChange={(checked) =>
            setForm({ ...form, is_default: checked === true })
          }
        />
        <Label htmlFor="llm-is-default" className="font-normal">
          {isEdit ? "Default LLM provider" : "Set as default LLM provider"}
        </Label>
      </div>
    </>
  )

  const footerButtons = (
    <>
      <div className="flex items-center gap-2">
        {isEdit && canDelete ? (
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
        {onCancel ? (
          <Button
            type="button"
            variant="outline"
            disabled={isPending}
            onClick={onCancel}
          >
            Cancel
          </Button>
        ) : null}
        <Button type="submit" disabled={isPending}>
          {isEdit ? "Save changes" : "Create provider"}
        </Button>
      </div>
    </>
  )

  const formTitle = isEdit
    ? "Edit LLM provider"
    : preset
      ? `Configure ${preset.label}`
      : "Add LLM provider"

  const formDescription = isEdit
    ? "Leave API token blank to keep the current value."
    : preset
      ? preset.description
      : "Register a new model endpoint for code reviews."

  return (
    <>
      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Delete LLM provider?"
        description={`Delete LLM provider "${provider?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteLlm.isPending}
        onConfirm={confirmDelete}
      />

      {isPage ? (
        <Card className="max-w-lg">
          <CardContent>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-3">{formFields}</div>
              <div
                className={cn(
                  "flex shrink-0 flex-row items-center justify-between gap-2 border-t pt-4",
                )}
              >
                {footerButtons}
              </div>
            </form>
          </CardContent>
        </Card>
      ) : (
        <>
          <DialogHeader className="shrink-0 border-b px-6 py-4">
            <DialogTitle>{formTitle}</DialogTitle>
            <DialogDescription>{formDescription}</DialogDescription>
          </DialogHeader>
          <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-3 overflow-y-auto px-6 py-4">
              {formFields}
            </div>
            <DialogFooter className="w-full shrink-0 flex-row items-center justify-between gap-2 border-t px-6 py-4 sm:justify-between">
              {footerButtons}
            </DialogFooter>
          </form>
        </>
      )}
    </>
  )
}

function LlmProviderCreateFlow({
  sessionKey,
  canDelete,
  onOpenChange,
  onDeleted,
  onStepChange,
}: {
  sessionKey: number
  canDelete: boolean
  onOpenChange: (open: boolean) => void
  onDeleted?: () => void
  onStepChange?: (onPicker: boolean) => void
}) {
  const [selectedPresetId, setSelectedPresetId] =
    useState<LlmProviderPresetId | null>(null)

  const preset = selectedPresetId
    ? getLlmProviderPreset(selectedPresetId)
    : undefined

  function selectPreset(presetId: LlmProviderPresetId) {
    setSelectedPresetId(presetId)
    onStepChange?.(false)
  }

  function goBackToPicker() {
    setSelectedPresetId(null)
    onStepChange?.(true)
  }

  if (selectedPresetId && preset) {
    return (
      <LlmProviderForm
        key={`create-${selectedPresetId}-${sessionKey}`}
        preset={preset}
        canDelete={canDelete}
        onSaved={() => onOpenChange(false)}
        onCancel={() => onOpenChange(false)}
        onBack={goBackToPicker}
        onDeleted={() => {
          onOpenChange(false)
          onDeleted?.()
        }}
      />
    )
  }

  return (
    <>
      <DialogHeader className="shrink-0 border-b px-6 py-4">
        <DialogTitle>Add LLM provider</DialogTitle>
        <DialogDescription>
          Choose a provider to register a model endpoint for code reviews.
        </DialogDescription>
      </DialogHeader>
      <ProviderPicker
        key={sessionKey}
        onSelect={selectPreset}
      />
    </>
  )
}

function LlmProviderCreateDialogContent({
  sessionKey,
  canDelete,
  onOpenChange,
  onDeleted,
}: {
  sessionKey: number
  canDelete: boolean
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
          : "sm:max-w-lg",
      )}
    >
      <LlmProviderCreateFlow
        sessionKey={sessionKey}
        canDelete={canDelete}
        onOpenChange={onOpenChange}
        onDeleted={onDeleted}
        onStepChange={setOnPicker}
      />
    </DialogContent>
  )
}

export function LlmProviderDialog({
  open,
  onOpenChange,
  provider,
  sessionKey,
  canDelete = true,
  onDeleted,
}: LlmProviderDialogProps) {
  const isEdit = Boolean(provider)
  const formKey = `${provider?.id ?? "create"}-${sessionKey}`

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open ? (
        isEdit ? (
          <DialogContent className="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
            <LlmProviderForm
              key={formKey}
              provider={provider}
              canDelete={canDelete}
              onSaved={() => onOpenChange(false)}
              onCancel={() => onOpenChange(false)}
              onDeleted={() => {
                onOpenChange(false)
                onDeleted?.()
              }}
            />
          </DialogContent>
        ) : (
          <LlmProviderCreateDialogContent
            key={sessionKey}
            sessionKey={sessionKey}
            canDelete={canDelete}
            onOpenChange={onOpenChange}
            onDeleted={onDeleted}
          />
        )
      ) : null}
    </Dialog>
  )
}
