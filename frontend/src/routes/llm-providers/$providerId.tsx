import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { AppShell } from "@/components/layout/AppShell"
import { LlmProviderForm } from "@/components/settings/LlmProviderDialog"
import { Skeleton } from "@/components/ui/skeleton"
import { useLlmProvider, useLlmProviders } from "@/hooks/use-settings"
import { requireOrgPermission } from "@/lib/permissions"
import { DEFAULT_LIST_SEARCH } from "@/lib/pagination"

export const Route = createFileRoute("/llm-providers/$providerId")({
  beforeLoad: requireOrgPermission("settings.llm.read"),
  component: LlmProviderDetailPage,
})

function LlmProviderDetailPage() {
  const { providerId } = Route.useParams()
  const navigate = useNavigate()
  const providerQuery = useLlmProvider(providerId)
  const allProviders = useLlmProviders()

  const provider = providerQuery.data
  const providerList = allProviders.data?.items ?? []

  const title = provider?.name ?? "LLM Provider"

  return (
    <AppShell
      title={title}
      description={
        provider
          ? `${provider.resolved_opencode_model} · ${provider.provider_id}`
          : undefined
      }
    >
      {providerQuery.isPending ? (
        <Skeleton className="h-96 max-w-lg" />
      ) : providerQuery.isError || !provider ? (
        <p className="text-destructive text-sm">LLM provider not found.</p>
      ) : (
        <LlmProviderForm
          key={`${provider.id}-${provider.updated_at}`}
          provider={provider}
          variant="page"
          canDelete={providerList.length > 1}
          onCancel={() => navigate({ to: "/llm-providers", search: DEFAULT_LIST_SEARCH })}
          onDeleted={() => navigate({ to: "/llm-providers", search: DEFAULT_LIST_SEARCH })}
        />
      )}
    </AppShell>
  )
}
