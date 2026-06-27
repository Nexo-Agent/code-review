import { useState } from "react"
import { toast } from "sonner"

import type { LlmProvider, LlmProviderCreate } from "@/api/settings-types"
import { Field } from "@/components/forms/Field"
import { ConfirmDialog } from "@/components/patterns/confirm-dialog"
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
import { emptyLlmForm, llmProviderIdOptions } from "@/lib/settings-constants"

type LlmProviderDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  provider?: LlmProvider | null
  sessionKey: number
  canDelete?: boolean
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

function LlmProviderForm({
  provider,
  onOpenChange,
  canDelete,
  onDeleted,
}: {
  provider?: LlmProvider | null
  onOpenChange: (open: boolean) => void
  canDelete?: boolean
  onDeleted?: () => void
}) {
  const isEdit = Boolean(provider)
  const createLlm = useCreateLlmProvider()
  const updateLlm = useUpdateLlmProvider()
  const deleteLlm = useDeleteLlmProvider()

  const [form, setForm] = useState(() => llmFormFromProvider(provider))
  const [apiToken, setApiToken] = useState("")
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

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
        const payload = { ...form }
        if (!payload.api_token) delete payload.api_token
        await createLlm.mutateAsync(payload)
        toast.success("LLM provider created")
      }
      onOpenChange(false)
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
      onOpenChange(false)
      onDeleted?.()
    } catch {
      toast.error("Failed to delete LLM provider")
    }
  }

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
      <DialogHeader className="shrink-0 border-b px-6 py-4">
        <DialogTitle>
          {isEdit ? "Edit LLM provider" : "Add LLM provider"}
        </DialogTitle>
        <DialogDescription>
          {isEdit
            ? "Leave API token blank to keep the current value."
            : "Register a new model endpoint for code reviews."}
        </DialogDescription>
      </DialogHeader>

      <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit}>
        <div className="flex flex-col gap-3 overflow-y-auto px-6 py-4">
          <Field label="Name">
            <Input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Field>
          <Field label="Provider ID">
            <Select
              value={form.provider_id}
              onValueChange={(value) =>
                setForm({ ...form, provider_id: value })
              }
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
          <Field label="Base URL">
            <Input
              required
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
            />
          </Field>
          <Field label="Model">
            <Input
              required
              value={form.model}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
              placeholder="e.g. gpt-4o"
            />
          </Field>
          <Field
            label={isEdit ? "API token (leave blank to keep)" : "API token"}
          >
            <Input
              type="password"
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
        </div>

        <DialogFooter className="shrink-0 border-t px-6 py-4">
          {isEdit && canDelete ? (
            <Button
              type="button"
              variant="destructive"
              disabled={isPending}
              onClick={() => setDeleteConfirmOpen(true)}
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
            {isEdit ? "Save changes" : "Create provider"}
          </Button>
        </DialogFooter>
      </form>
    </>
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
  const formKey = `${provider?.id ?? "create"}-${sessionKey}`

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
        {open ? (
          <LlmProviderForm
            key={formKey}
            provider={provider}
            onOpenChange={onOpenChange}
            canDelete={canDelete}
            onDeleted={onDeleted}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
