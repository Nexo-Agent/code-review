import { createFileRoute, useNavigate, redirect } from "@tanstack/react-router"

import { AppShell } from "@/components/layout/AppShell"
import { LlmProviderForm } from "@/components/settings/LlmProviderDialog"
import { Skeleton } from "@/components/ui/skeleton"
import { useLlmProvider, useLlmProviders } from "@/hooks/use-settings"

export const Route = createFileRoute("/llm-providers/$providerId")({
  beforeLoad: ({ context }) => {
    const me = (context as { me?: { user: { is_org_admin: boolean } } }).me
    if (me && !me.user.is_org_admin) {
      throw redirect({ to: "/teams" })
    }
  },
  component: LlmProviderDetailPage,
})

function LlmProviderDetailPage() {
  const { providerId } = Route.useParams()
  const navigate = useNavigate()
  const providerQuery = useLlmProvider(providerId)
  const allProviders = useLlmProviders()

  const provider = providerQuery.data
  const providerList = allProviders.data ?? []

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
          onCancel={() => navigate({ to: "/llm-providers" })}
          onDeleted={() => navigate({ to: "/llm-providers" })}
        />
      )}
    </AppShell>
  )
}
