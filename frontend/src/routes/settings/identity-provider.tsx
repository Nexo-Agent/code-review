import { createFileRoute, redirect } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import type {
  IdentityProvider,
  IdentityProviderPreset,
  IdentityProviderProtocol,
  IdentityProviderUpsertPayload,
} from "@/api/identity-provider-types"
import { Field } from "@/components/forms/Field"
import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import {
  useDeleteIdentityProvider,
  useIdentityProvider,
  useUploadSamlSpCert,
  useUpsertIdentityProvider,
} from "@/hooks/use-identity-provider"

export const Route = createFileRoute("/settings/identity-provider")({
  beforeLoad: ({ context }) => {
    const me = (context as { me?: { user: { is_org_admin: boolean } } }).me
    if (me && !me.user.is_org_admin) {
      throw redirect({ to: "/teams" })
    }
  },
  component: IdentityProviderSettingsPage,
})

const OIDC_PRESETS: { value: IdentityProviderPreset; label: string }[] = [
  { value: "google", label: "Google Workspace" },
  { value: "entra", label: "Microsoft Entra ID" },
  { value: "okta", label: "Okta" },
  { value: "keycloak", label: "Keycloak" },
  { value: "auth0", label: "Auth0" },
  { value: "custom", label: "Custom OIDC" },
]

function IdentityProviderSettingsPage() {
  const idp = useIdentityProvider()
  const remove = useDeleteIdentityProvider()
  const configured = idp.data != null

  async function handleDelete() {
    try {
      await remove.mutateAsync()
      toast.success("Identity provider removed")
    } catch {
      toast.error("Failed to remove identity provider")
    }
  }

  return (
    <AppShell
      title="SSO / Identity Provider"
      description="Configure a single OIDC or SAML 2.0 identity provider for this organization."
      actions={
        configured ? (
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
        <IdentityProviderForm
          key={idp.data?.updated_at ?? "new"}
          initial={idp.data ?? null}
        />
      </DataPanel>
    </AppShell>
  )
}

function IdentityProviderForm({ initial }: { initial: IdentityProvider | null }) {
  const upsert = useUpsertIdentityProvider()
  const uploadCert = useUploadSamlSpCert()

  const [protocol, setProtocol] = useState<IdentityProviderProtocol>(
    initial?.protocol ?? "oidc",
  )
  const [preset, setPreset] = useState<IdentityProviderPreset>(
    initial?.preset ?? "google",
  )
  const [enabled, setEnabled] = useState(initial?.enabled ?? false)
  const [displayName, setDisplayName] = useState(initial?.display_name ?? "")
  const [oidcClientId, setOidcClientId] = useState(initial?.oidc_client_id ?? "")
  const [oidcClientSecret, setOidcClientSecret] = useState("")
  const [oidcIssuer, setOidcIssuer] = useState(initial?.oidc_issuer ?? "")
  const [presetTenantId, setPresetTenantId] = useState("")
  const [presetDomain, setPresetDomain] = useState("")
  const [presetBaseUrl, setPresetBaseUrl] = useState("")
  const [presetRealm, setPresetRealm] = useState("")
  const [samlMetadataUrl, setSamlMetadataUrl] = useState("")
  const [samlMetadataXml, setSamlMetadataXml] = useState("")
  const [samlEntityId, setSamlEntityId] = useState(initial?.saml_idp_entity_id ?? "")
  const [samlSsoUrl, setSamlSsoUrl] = useState(initial?.saml_idp_sso_url ?? "")
  const [samlCert, setSamlCert] = useState("")
  const [spCert, setSpCert] = useState("")
  const [spPrivateKey, setSpPrivateKey] = useState("")

  async function handleSave() {
    const payload: IdentityProviderUpsertPayload = {
      protocol,
      preset: protocol === "saml" ? "custom" : preset,
      enabled,
      display_name: displayName,
      oidc_client_id: oidcClientId || null,
      oidc_client_secret: oidcClientSecret || null,
      oidc_issuer: oidcIssuer || null,
      preset_tenant_id: presetTenantId || null,
      preset_domain: presetDomain || null,
      preset_base_url: presetBaseUrl || null,
      preset_realm: presetRealm || null,
      saml_idp_metadata_url: samlMetadataUrl || null,
      saml_idp_metadata_xml: samlMetadataXml || null,
      saml_idp_entity_id: samlEntityId || null,
      saml_idp_sso_url: samlSsoUrl || null,
      saml_idp_cert: samlCert || null,
    }
    try {
      await upsert.mutateAsync(payload)
      toast.success("Identity provider saved")
      setOidcClientSecret("")
    } catch {
      toast.error("Failed to save identity provider")
    }
  }

  async function handleUploadCert() {
    if (!spCert.trim() || !spPrivateKey.trim()) return
    try {
      await uploadCert.mutateAsync({
        sp_cert: spCert,
        sp_private_key: spPrivateKey,
      })
      toast.success("SP certificate uploaded")
      setSpCert("")
      setSpPrivateKey("")
    } catch {
      toast.error("Failed to upload SP certificate")
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between rounded-lg border p-4">
        <div>
          <p className="text-sm font-medium">Enabled</p>
          <p className="text-muted-foreground text-xs">
            Users must sign in through the configured provider when auth is on.
          </p>
        </div>
        <Switch checked={enabled} onCheckedChange={setEnabled} />
      </div>

      <Field label="Protocol">
        <Select
          value={protocol}
          onValueChange={(value) => setProtocol(value as IdentityProviderProtocol)}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value="oidc">OpenID Connect (OIDC)</SelectItem>
              <SelectItem value="saml">SAML 2.0</SelectItem>
            </SelectGroup>
          </SelectContent>
        </Select>
      </Field>

      {protocol === "oidc" ? (
        <>
          <Field label="Provider preset">
            <Select
              value={preset}
              onValueChange={(value) => setPreset(value as IdentityProviderPreset)}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {OIDC_PRESETS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>

          {preset === "entra" ? (
            <Field label="Tenant ID">
              <Input
                value={presetTenantId}
                onChange={(e) => setPresetTenantId(e.target.value)}
              />
            </Field>
          ) : null}

          {preset === "okta" || preset === "auth0" ? (
            <Field label="Domain">
              <Input
                value={presetDomain}
                onChange={(e) => setPresetDomain(e.target.value)}
                placeholder="your-org.okta.com"
              />
            </Field>
          ) : null}

          {preset === "keycloak" ? (
            <>
              <Field label="Base URL">
                <Input
                  value={presetBaseUrl}
                  onChange={(e) => setPresetBaseUrl(e.target.value)}
                  placeholder="https://keycloak.example.com"
                />
              </Field>
              <Field label="Realm">
                <Input
                  value={presetRealm}
                  onChange={(e) => setPresetRealm(e.target.value)}
                />
              </Field>
            </>
          ) : null}

          {preset === "custom" ? (
            <Field label="Issuer URL">
              <Input value={oidcIssuer} onChange={(e) => setOidcIssuer(e.target.value)} />
            </Field>
          ) : null}

          <Field label="Client ID">
            <Input value={oidcClientId} onChange={(e) => setOidcClientId(e.target.value)} />
          </Field>

          <Field label="Client secret">
            {initial?.oidc_client_secret_configured ? (
              <p className="text-muted-foreground mb-1 text-xs">
                Leave blank to keep the current secret.
              </p>
            ) : null}
            <Input
              type="password"
              value={oidcClientSecret}
              onChange={(e) => setOidcClientSecret(e.target.value)}
            />
          </Field>

          <Field label="Redirect URI (register in IdP)">
            <Input
              value={
                initial?.oidc_redirect_uri ??
                `${window.location.origin}/api/v1/auth/callback`
              }
              readOnly
            />
          </Field>
        </>
      ) : (
        <>
          <Field label="IdP metadata URL">
            <Input
              value={samlMetadataUrl}
              onChange={(e) => setSamlMetadataUrl(e.target.value)}
              placeholder="https://idp.example.com/metadata"
            />
          </Field>

          <Field label="Or paste IdP metadata XML">
            <Textarea
              value={samlMetadataXml}
              onChange={(e) => setSamlMetadataXml(e.target.value)}
              rows={6}
            />
          </Field>

          <Field label="IdP entity ID (manual override)">
            <Input value={samlEntityId} onChange={(e) => setSamlEntityId(e.target.value)} />
          </Field>

          <Field label="IdP SSO URL (manual override)">
            <Input value={samlSsoUrl} onChange={(e) => setSamlSsoUrl(e.target.value)} />
          </Field>

          <Field label="IdP X.509 certificate (manual override)">
            <Textarea value={samlCert} onChange={(e) => setSamlCert(e.target.value)} rows={4} />
          </Field>

          <Field label="SP metadata URL (register in IdP)">
            <Input
              value={
                initial?.saml_metadata_url ??
                `${window.location.origin}/api/v1/auth/saml/metadata`
              }
              readOnly
            />
          </Field>

          {initial?.saml_sp_cert_configured ? (
            <div className="space-y-4 rounded-lg border p-4">
              <p className="text-sm font-medium">Replace SP certificate (optional)</p>
              <Field label="SP certificate PEM">
                <Textarea value={spCert} onChange={(e) => setSpCert(e.target.value)} rows={4} />
              </Field>
              <Field label="SP private key PEM">
                <Textarea
                  value={spPrivateKey}
                  onChange={(e) => setSpPrivateKey(e.target.value)}
                  rows={4}
                />
              </Field>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={uploadCert.isPending}
                onClick={handleUploadCert}
              >
                Upload SP certificate
              </Button>
            </div>
          ) : null}
        </>
      )}

      <Field label="Login button label">
        <Input
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Google Workspace"
        />
      </Field>

      <Button type="button" disabled={upsert.isPending} onClick={handleSave}>
        Save configuration
      </Button>
    </div>
  )
}
