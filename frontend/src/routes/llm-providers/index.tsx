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
  useCreateLlmProvider,
  useDeleteLlmProvider,
  useLlmProviders,
} from "@/hooks/use-settings"
import { emptyLlmForm, llmProviderIdOptions } from "@/lib/settings-constants"

export const Route = createFileRoute("/llm-providers/")({
  component: LlmProvidersPage,
})

function LlmProvidersPage() {
  const providers = useLlmProviders()
  const createLlm = useCreateLlmProvider()
  const deleteLlm = useDeleteLlmProvider()

  const [showAddForm, setShowAddForm] = useState(false)
  const [newLlm, setNewLlm] = useState(emptyLlmForm)

  const providerList = providers.data ?? []

  async function handleCreateLlm(event: React.FormEvent) {
    event.preventDefault()
    try {
      const payload = { ...newLlm }
      if (!payload.api_token) delete payload.api_token
      await createLlm.mutateAsync(payload)
      setNewLlm(emptyLlmForm())
      setShowAddForm(false)
      toast.success("LLM provider created")
    } catch {
      toast.error("Failed to create LLM provider")
    }
  }

  return (
    <AppShell
      title="LLM Providers"
      description={`${providerList.length} provider${providerList.length === 1 ? "" : "s"} · OpenCode model endpoints`}
      actions={
        <Button
          type="button"
          size="sm"
          variant={showAddForm ? "outline" : "default"}
          onClick={() => setShowAddForm((v) => !v)}
        >
          {showAddForm ? "Cancel" : "Add provider"}
        </Button>
      }
    >
      {showAddForm ? (
        <Card className="mb-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Add LLM provider</CardTitle>
            <CardDescription>
              Register a new model endpoint for code reviews.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="flex flex-col gap-3" onSubmit={handleCreateLlm}>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Name">
                  <Input
                    required
                    value={newLlm.name}
                    onChange={(e) =>
                      setNewLlm({ ...newLlm, name: e.target.value })
                    }
                  />
                </Field>
                <Field label="Provider ID">
                  <Select
                    required
                    value={newLlm.provider_id}
                    onChange={(e) =>
                      setNewLlm({ ...newLlm, provider_id: e.target.value })
                    }
                  >
                    {llmProviderIdOptions(newLlm.provider_id).map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Base URL">
                  <Input
                    required
                    value={newLlm.base_url}
                    onChange={(e) =>
                      setNewLlm({ ...newLlm, base_url: e.target.value })
                    }
                  />
                </Field>
                <Field label="Model">
                  <Input
                    required
                    value={newLlm.model}
                    onChange={(e) =>
                      setNewLlm({ ...newLlm, model: e.target.value })
                    }
                  />
                </Field>
                <Field label="API token">
                  <Input
                    type="password"
                    value={newLlm.api_token ?? ""}
                    onChange={(e) =>
                      setNewLlm({ ...newLlm, api_token: e.target.value })
                    }
                  />
                </Field>
                <Field label="OpenCode model override">
                  <Input
                    value={newLlm.opencode_model ?? ""}
                    onChange={(e) =>
                      setNewLlm({
                        ...newLlm,
                        opencode_model: e.target.value,
                      })
                    }
                  />
                </Field>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newLlm.is_default ?? false}
                  onChange={(e) =>
                    setNewLlm({ ...newLlm, is_default: e.target.checked })
                  }
                />
                Set as default LLM provider
              </label>
              <div>
                <Button type="submit" size="sm" disabled={createLlm.isPending}>
                  Create LLM provider
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <div className="rounded-lg border">
        {providers.isPending ? (
          <div className="flex flex-col gap-1.5 p-3">
            <Skeleton className="h-7 w-full" />
            <Skeleton className="h-7 w-full" />
          </div>
        ) : providers.isError ? (
          <p className="text-destructive p-3 text-sm">
            Could not load LLM providers. Run{" "}
            <code className="text-xs">make dev</code> first.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Default</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {providerList.length ? (
                providerList.map((provider) => (
                  <TableRow key={provider.id}>
                    <TableCell>
                      <Link
                        to="/llm-providers/$providerId"
                        params={{ providerId: provider.id }}
                        className="font-medium hover:underline"
                      >
                        {provider.name}
                      </Link>
                      <p className="text-muted-foreground text-xs">
                        {provider.provider_id}
                      </p>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {provider.resolved_opencode_model}
                    </TableCell>
                    <TableCell>
                      {provider.is_default ? (
                        <Badge
                          variant="secondary"
                          className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                        >
                          Default
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive h-7 px-2"
                        disabled={providerList.length <= 1}
                        onClick={async () => {
                          if (
                            !confirm(
                              `Delete LLM provider "${provider.name}"?`,
                            )
                          ) {
                            return
                          }
                          try {
                            await deleteLlm.mutateAsync(provider.id)
                            toast.success("LLM provider deleted")
                          } catch {
                            toast.error("Failed to delete LLM provider")
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
                    colSpan={4}
                    className="text-muted-foreground h-12 text-center"
                  >
                    No LLM providers yet. Click &quot;Add provider&quot; to get
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
