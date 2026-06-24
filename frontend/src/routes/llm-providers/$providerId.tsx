import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import type { LlmProvider } from "@/api/settings-types"
import { Field } from "@/components/forms/Field"
import { AppShell } from "@/components/layout/AppShell"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useDeleteLlmProvider,
  useLlmProvider,
  useUpdateLlmProvider,
} from "@/hooks/use-settings"

export const Route = createFileRoute("/llm-providers/$providerId")({
  component: LlmProviderDetailPage,
})

function LlmProviderDetailPage() {
  const { providerId } = Route.useParams()
  const navigate = useNavigate()
  const providerQuery = useLlmProvider(providerId)
  const updateLlm = useUpdateLlmProvider()
  const deleteLlm = useDeleteLlmProvider()

  const provider = providerQuery.data
  const [draft, setDraft] = useState<LlmProvider | null>(null)
  const [apiToken, setApiToken] = useState("")

  const editing = draft ?? provider

  async function handleSave() {
    if (!editing) return
    try {
      await updateLlm.mutateAsync({
        id: editing.id,
        payload: {
          name: editing.name,
          provider_id: editing.provider_id,
          base_url: editing.base_url,
          model: editing.model,
          opencode_model: editing.opencode_model,
          is_default: editing.is_default,
          ...(apiToken ? { api_token: apiToken } : {}),
        },
      })
      setDraft(null)
      setApiToken("")
      toast.success("LLM provider updated — restart opencode-serve to apply")
    } catch {
      toast.error("Failed to update LLM provider")
    }
  }

  async function handleDelete() {
    if (!provider) return
    if (!confirm(`Delete LLM provider "${provider.name}"?`)) return
    try {
      await deleteLlm.mutateAsync(provider.id)
      toast.success("LLM provider deleted")
      await navigate({ to: "/llm-providers" })
    } catch {
      toast.error("Failed to delete LLM provider")
    }
  }

  return (
    <AppShell title={provider?.name ?? "LLM Provider"}>
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/llm-providers">← Back to LLM providers</Link>
        </Button>
      </div>

      {providerQuery.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : providerQuery.isError || !provider ? (
        <p className="text-destructive text-sm">LLM provider not found.</p>
      ) : editing ? (
        <Card>
          <CardHeader>
            <CardTitle>Provider configuration</CardTitle>
            <CardDescription>
              Update model endpoint settings. Leave API token blank to keep the
              current value.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Name">
                  <Input
                    value={editing.name}
                    onChange={(e) =>
                      setDraft({ ...editing, name: e.target.value })
                    }
                  />
                </Field>
                <Field label="Provider ID">
                  <Input
                    value={editing.provider_id}
                    onChange={(e) =>
                      setDraft({ ...editing, provider_id: e.target.value })
                    }
                  />
                </Field>
                <Field label="Base URL">
                  <Input
                    value={editing.base_url}
                    onChange={(e) =>
                      setDraft({ ...editing, base_url: e.target.value })
                    }
                  />
                </Field>
                <Field label="Model">
                  <Input
                    value={editing.model}
                    onChange={(e) =>
                      setDraft({ ...editing, model: e.target.value })
                    }
                  />
                </Field>
                <Field label="OpenCode model override">
                  <Input
                    value={editing.opencode_model}
                    onChange={(e) =>
                      setDraft({
                        ...editing,
                        opencode_model: e.target.value,
                      })
                    }
                  />
                </Field>
                <Field label="API token (leave blank to keep)">
                  <Input
                    type="password"
                    value={apiToken}
                    onChange={(e) => setApiToken(e.target.value)}
                    placeholder={
                      provider.api_token_configured ? "Configured" : "Not set"
                    }
                  />
                </Field>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editing.is_default}
                  onChange={(e) =>
                    setDraft({ ...editing, is_default: e.target.checked })
                  }
                />
                Default LLM provider
              </label>
              <p className="text-muted-foreground text-xs">
                Resolved model: {provider.resolved_opencode_model}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  onClick={handleSave}
                  disabled={updateLlm.isPending}
                >
                  Save changes
                </Button>
                {draft ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setDraft(null)
                      setApiToken("")
                    }}
                  >
                    Reset
                  </Button>
                ) : null}
                <Button
                  type="button"
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleteLlm.isPending}
                >
                  Delete provider
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </AppShell>
  )
}
