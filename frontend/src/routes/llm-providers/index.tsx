import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { EmptyState } from "@/components/patterns/empty-state"
import { PaginatedListPanel } from "@/components/patterns/paginated-list-panel"
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
import { useLlmProvidersPage, useUpdateLlmProvider } from "@/hooks/use-settings"
import { parsePageSearch, DEFAULT_LIST_SEARCH } from "@/lib/pagination"

export const Route = createFileRoute("/llm-providers/")({
  beforeLoad: ({ context }) => {
    const me = (context as { me?: { user: { is_org_admin: boolean } } }).me
    if (me && !me.user.is_org_admin) {
      throw redirect({ to: "/teams", search: DEFAULT_LIST_SEARCH })
    }
  },
  validateSearch: parsePageSearch,
  component: LlmProvidersPage,
})

function LlmProvidersPage() {
  const navigate = Route.useNavigate()
  const { page } = Route.useSearch()
  const providers = useLlmProvidersPage({ page })
  const updateLlm = useUpdateLlmProvider()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogSession, setDialogSession] = useState(0)

  const total = providers.data?.total ?? 0

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

  function goToPage(nextPage: number) {
    void navigate({ search: { page: nextPage, q: "" } })
  }

  return (
    <AppShell
      title="LLM Providers"
      description={`${total} provider${total === 1 ? "" : "s"}`}
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
        canDelete={total > 1}
      />

      <PaginatedListPanel
        query={providers}
        page={page}
        onPageChange={goToPage}
      >
        {(providerList) => (
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
        )}
      </PaginatedListPanel>
    </AppShell>
  )
}
