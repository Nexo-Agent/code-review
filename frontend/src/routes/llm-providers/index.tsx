import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { EmptyState } from "@/components/patterns/empty-state"
import { CodeHint } from "@/components/patterns/inline-error"
import { LlmProviderDialog } from "@/components/settings/LlmProviderDialog"
import { Badge } from "@/components/ui/badge"
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
import { useLlmProviders, useUpdateLlmProvider } from "@/hooks/use-settings"

export const Route = createFileRoute("/llm-providers/")({
  component: LlmProvidersPage,
})

function LlmProvidersPage() {
  const providers = useLlmProviders()
  const updateLlm = useUpdateLlmProvider()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogSession, setDialogSession] = useState(0)

  const providerList = providers.data ?? []

  function openCreate() {
    setDialogSession((session) => session + 1)
    setDialogOpen(true)
  }

  async function toggleEnabled(providerId: string, enabled: boolean) {
    try {
      await updateLlm.mutateAsync({ id: providerId, payload: { enabled } })
      toast.success(enabled ? "LLM provider enabled" : "LLM provider disabled")
    } catch {
      toast.error("Failed to update LLM provider")
    }
  }

  return (
    <AppShell
      title="LLM Providers"
      actions={
        <Button type="button" size="sm" onClick={openCreate}>
          Add provider
        </Button>
      }
    >
      <LlmProviderDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        provider={null}
        sessionKey={dialogSession}
        canDelete={providerList.length > 1}
      />

      <DataPanel
        loading={providers.isPending}
        error={providers.isError}
        errorMessage="Could not load LLM providers. Run"
        errorHint={<CodeHint>make dev</CodeHint>}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Default</TableHead>
              <TableHead className="w-20 text-right">Enabled</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {providerList.length ? (
              providerList.map((provider) => (
                <TableRow key={provider.id}>
                  <TableCell>
                    <span className="font-medium">{provider.name}</span>
                    <p className="text-muted-foreground text-xs">
                      {provider.provider_id}
                    </p>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {provider.resolved_opencode_model}
                  </TableCell>
                  <TableCell>
                    {provider.is_default ? (
                      <Badge variant="success">Default</Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Switch
                      checked={provider.enabled}
                      disabled={updateLlm.isPending}
                      onCheckedChange={(enabled) =>
                        void toggleEnabled(provider.id, enabled)
                      }
                      aria-label={
                        provider.enabled
                          ? `Disable ${provider.name}`
                          : `Enable ${provider.name}`
                      }
                    />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <EmptyState colSpan={4}>
                No LLM providers yet. Click &quot;Add provider&quot; to get
                started.
              </EmptyState>
            )}
          </TableBody>
        </Table>
      </DataPanel>
    </AppShell>
  )
}
