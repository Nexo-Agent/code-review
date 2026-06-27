import { Link } from "@tanstack/react-router"
import { Pencil } from "lucide-react"

import type { IdentityProvider } from "@/api/identity-provider-types"
import { ProviderLogo } from "@/components/settings/identity-provider/ProviderLogo"
import { getSsoProviderForConfig } from "@/components/settings/identity-provider/providers"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type ConfiguredIdpViewProps = {
  config: IdentityProvider
}

export function ConfiguredIdpView({ config }: ConfiguredIdpViewProps) {
  const provider = getSsoProviderForConfig(config.protocol, config.preset)

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <Card className="border">
        <CardHeader className="flex flex-row items-center gap-4">
          <ProviderLogo providerId={provider.id} className="size-12" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-xl">{config.display_name}</CardTitle>
              <Badge variant="outline">
                {config.protocol === "oidc" ? "OpenID Connect" : "SAML 2.0"}
              </Badge>
            </div>
          </div>
          <Button type="button" variant="outline" size="sm" asChild>
            <Link
              to="/settings/identity-provider"
              search={{ setup: undefined, edit: true }}
            >
              <Pencil data-icon="inline-start" />
              Edit
            </Link>
          </Button>
        </CardHeader>

        <CardContent className="flex flex-col gap-4">
          {config.protocol === "oidc" ? (
            <OidcDetails config={config} />
          ) : (
            <SamlDetails config={config} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground text-xs font-medium">{label}</span>
      <span className="font-mono text-sm break-all">{value}</span>
    </div>
  )
}

function OidcDetails({ config }: { config: IdentityProvider }) {
  return (
    <>
      <DetailRow label="Client ID" value={config.oidc_client_id} />
      <DetailRow label="Issuer" value={config.oidc_issuer} />
      <DetailRow
        label="Client secret"
        value={config.oidc_client_secret_configured ? "Configured" : "Not set"}
      />
      <DetailRow label="Redirect URI" value={config.oidc_redirect_uri} />
      <DetailRow label="Scopes" value={config.oidc_scopes} />
    </>
  )
}

function SamlDetails({ config }: { config: IdentityProvider }) {
  return (
    <>
      <DetailRow label="IdP entity ID" value={config.saml_idp_entity_id} />
      <DetailRow label="IdP SSO URL" value={config.saml_idp_sso_url} />
      <DetailRow
        label="IdP certificate"
        value={config.saml_idp_cert_configured ? "Configured" : "Not set"}
      />
      <DetailRow label="SP metadata URL" value={config.saml_metadata_url} />
      <DetailRow
        label="SP certificate"
        value={config.saml_sp_cert_configured ? "Configured" : "Not set"}
      />
    </>
  )
}
