import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"
import { toast } from "sonner"

import { ConfiguredIdpView } from "@/components/settings/identity-provider/ConfiguredIdpView"
import { IdentityProviderForm } from "@/components/settings/identity-provider/IdentityProviderForm"
import { ProviderPicker } from "@/components/settings/identity-provider/ProviderPicker"
import {
  getSsoProvider,
  getSsoProviderForConfig,
  type SsoProviderId,
} from "@/components/settings/identity-provider/providers"
import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { Button } from "@/components/ui/button"
import {
  useDeleteIdentityProvider,
  useIdentityProvider,
} from "@/hooks/use-identity-provider"
import { DEFAULT_LIST_SEARCH } from "@/lib/pagination"

const SETUP_PROVIDER_IDS = [
  "google",
  "entra",
  "okta",
  "keycloak",
  "auth0",
  "custom",
  "saml",
] as const

function parseSetupProvider(value: unknown): SsoProviderId | undefined {
  if (typeof value !== "string") return undefined
  return SETUP_PROVIDER_IDS.includes(value as SsoProviderId)
    ? (value as SsoProviderId)
    : undefined
}

export const Route = createFileRoute("/settings/identity-provider")({
  validateSearch: (search: Record<string, unknown>) => ({
    setup: parseSetupProvider(search.setup),
    edit: search.edit === true || search.edit === "true",
  }),
  beforeLoad: ({ context }) => {
    const me = (context as { me?: { user: { is_org_admin: boolean } } }).me
    if (me && !me.user.is_org_admin) {
      throw redirect({ to: "/teams", search: DEFAULT_LIST_SEARCH })
    }
  },
  component: IdentityProviderSettingsPage,
})

function IdentityProviderSettingsPage() {
  const navigate = useNavigate({ from: Route.fullPath })
  const { setup, edit } = Route.useSearch()
  const idp = useIdentityProvider()
  const remove = useDeleteIdentityProvider()
  const configured = idp.data != null

  async function handleDelete() {
    try {
      await remove.mutateAsync()
      toast.success("Identity provider removed")
      void navigate({ search: { setup: undefined, edit: false } })
    } catch {
      toast.error("Failed to remove identity provider")
    }
  }

  function handleSaved() {
    void navigate({ search: { setup: undefined, edit: false } })
  }

  const showForm = Boolean(setup) || (configured && edit)
  const setupProvider = setup ? getSsoProvider(setup) : null
  const editProvider =
    configured && edit ? getSsoProviderForConfig(idp.data!.protocol, idp.data!.preset) : null
  const formProvider = setupProvider ?? editProvider

  const title = showForm
    ? formProvider
      ? `Configure ${formProvider.label}`
      : "SSO / Identity Provider"
    : configured
      ? "SSO / Identity Provider"
      : "Set up SSO"

  const description = showForm
    ? formProvider?.description
    : configured
      ? "Your organization identity provider configuration."
      : "Choose a provider to enable single sign-on for your organization."

  return (
    <AppShell
      title={title}
      description={description}
      actions={
        configured && !showForm ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={remove.isPending}
            onClick={handleDelete}
          >
            Remove
          </Button>
        ) : undefined
      }
    >
      <DataPanel loading={idp.isPending} error={idp.isError}>
        {showForm && formProvider ? (
          <IdentityProviderForm
            key={`${formProvider.id}-${idp.data?.updated_at ?? "new"}`}
            provider={formProvider}
            initial={idp.data ?? null}
            onSaved={handleSaved}
          />
        ) : configured && idp.data ? (
          <ConfiguredIdpView config={idp.data} />
        ) : (
          <ProviderPicker />
        )}
      </DataPanel>
    </AppShell>
  )
}
