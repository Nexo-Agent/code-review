import { Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import type {
  IdentityProvider,
  IdentityProviderPreset,
  IdentityProviderProtocol,
  IdentityProviderUpsertPayload,
} from "@/api/identity-provider-types"
import { Field } from "@/components/forms/Field"
import { ProviderLogo } from "@/components/settings/identity-provider/ProviderLogo"
import {
  type SsoProviderDefinition,
} from "@/components/settings/identity-provider/providers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  useUploadSamlSpCert,
  useUpsertIdentityProvider,
} from "@/hooks/use-identity-provider"

type IdentityProviderFormProps = {
  provider: SsoProviderDefinition
  initial: IdentityProvider | null
  onSaved?: () => void
}

export function IdentityProviderForm({
  provider,
  initial,
  onSaved,
}: IdentityProviderFormProps) {
  const upsert = useUpsertIdentityProvider()
  const uploadCert = useUploadSamlSpCert()

  const protocol: IdentityProviderProtocol = provider.protocol
  const preset: IdentityProviderPreset = provider.preset

  const [displayName, setDisplayName] = useState(
    initial?.display_name ?? provider.defaultDisplayName,
  )
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
      enabled: true,
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
      onSaved?.()
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
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex items-center gap-3">
        {!initial ? (
          <Button type="button" variant="ghost" size="sm" asChild>
            <Link
              to="/settings/identity-provider"
              search={{ setup: undefined, edit: false }}
            >
              <ArrowLeft data-icon="inline-start" />
              Back
            </Link>
          </Button>
        ) : (
          <Button type="button" variant="ghost" size="sm" asChild>
            <Link
              to="/settings/identity-provider"
              search={{ setup: undefined, edit: false }}
            >
              <ArrowLeft data-icon="inline-start" />
              Cancel
            </Link>
          </Button>
        )}
      </div>

      <div className="flex items-center gap-4 rounded-lg border p-4">
        <ProviderLogo providerId={provider.id} className="size-12" />
        <div className="min-w-0 flex-1">
          <p className="font-medium">{provider.label}</p>
          <p className="text-muted-foreground text-sm">{provider.description}</p>
        </div>
      </div>

      {protocol === "oidc" ? (
        <OidcFields
          preset={preset}
          initial={initial}
          presetTenantId={presetTenantId}
          setPresetTenantId={setPresetTenantId}
          presetDomain={presetDomain}
          setPresetDomain={setPresetDomain}
          presetBaseUrl={presetBaseUrl}
          setPresetBaseUrl={setPresetBaseUrl}
          presetRealm={presetRealm}
          setPresetRealm={setPresetRealm}
          oidcIssuer={oidcIssuer}
          setOidcIssuer={setOidcIssuer}
          oidcClientId={oidcClientId}
          setOidcClientId={setOidcClientId}
          oidcClientSecret={oidcClientSecret}
          setOidcClientSecret={setOidcClientSecret}
        />
      ) : (
        <SamlFields
          initial={initial}
          samlMetadataUrl={samlMetadataUrl}
          setSamlMetadataUrl={setSamlMetadataUrl}
          samlMetadataXml={samlMetadataXml}
          setSamlMetadataXml={setSamlMetadataXml}
          samlEntityId={samlEntityId}
          setSamlEntityId={setSamlEntityId}
          samlSsoUrl={samlSsoUrl}
          setSamlSsoUrl={setSamlSsoUrl}
          samlCert={samlCert}
          setSamlCert={setSamlCert}
          spCert={spCert}
          setSpCert={setSpCert}
          spPrivateKey={spPrivateKey}
          setSpPrivateKey={setSpPrivateKey}
          onUploadCert={handleUploadCert}
          uploadPending={uploadCert.isPending}
        />
      )}

      <Field label="Login button label">
        <Input
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder={provider.defaultDisplayName}
        />
      </Field>

      <Button type="button" disabled={upsert.isPending} onClick={handleSave}>
        Save configuration
      </Button>
    </div>
  )
}

type OidcFieldsProps = {
  preset: IdentityProviderPreset
  initial: IdentityProvider | null
  presetTenantId: string
  setPresetTenantId: (value: string) => void
  presetDomain: string
  setPresetDomain: (value: string) => void
  presetBaseUrl: string
  setPresetBaseUrl: (value: string) => void
  presetRealm: string
  setPresetRealm: (value: string) => void
  oidcIssuer: string
  setOidcIssuer: (value: string) => void
  oidcClientId: string
  setOidcClientId: (value: string) => void
  oidcClientSecret: string
  setOidcClientSecret: (value: string) => void
}

function OidcFields({
  preset,
  initial,
  presetTenantId,
  setPresetTenantId,
  presetDomain,
  setPresetDomain,
  presetBaseUrl,
  setPresetBaseUrl,
  presetRealm,
  setPresetRealm,
  oidcIssuer,
  setOidcIssuer,
  oidcClientId,
  setOidcClientId,
  oidcClientSecret,
  setOidcClientSecret,
}: OidcFieldsProps) {
  return (
    <div className="flex flex-col gap-4">
      {preset === "entra" ? (
        <Field label="Tenant ID">
          <Input
            value={presetTenantId}
            onChange={(e) => setPresetTenantId(e.target.value)}
            placeholder="00000000-0000-0000-0000-000000000000"
          />
        </Field>
      ) : null}

      {preset === "okta" || preset === "auth0" ? (
        <Field label="Domain">
          <Input
            value={presetDomain}
            onChange={(e) => setPresetDomain(e.target.value)}
            placeholder={
              preset === "okta" ? "your-org.okta.com" : "your-tenant.auth0.com"
            }
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
              placeholder="master"
            />
          </Field>
        </>
      ) : null}

      {preset === "custom" ? (
        <Field label="Issuer URL">
          <Input
            value={oidcIssuer}
            onChange={(e) => setOidcIssuer(e.target.value)}
            placeholder="https://idp.example.com"
          />
        </Field>
      ) : null}

      <Field label="Client ID">
        <Input
          value={oidcClientId}
          onChange={(e) => setOidcClientId(e.target.value)}
        />
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
    </div>
  )
}

type SamlFieldsProps = {
  initial: IdentityProvider | null
  samlMetadataUrl: string
  setSamlMetadataUrl: (value: string) => void
  samlMetadataXml: string
  setSamlMetadataXml: (value: string) => void
  samlEntityId: string
  setSamlEntityId: (value: string) => void
  samlSsoUrl: string
  setSamlSsoUrl: (value: string) => void
  samlCert: string
  setSamlCert: (value: string) => void
  spCert: string
  setSpCert: (value: string) => void
  spPrivateKey: string
  setSpPrivateKey: (value: string) => void
  onUploadCert: () => void
  uploadPending: boolean
}

function SamlFields({
  initial,
  samlMetadataUrl,
  setSamlMetadataUrl,
  samlMetadataXml,
  setSamlMetadataXml,
  samlEntityId,
  setSamlEntityId,
  samlSsoUrl,
  setSamlSsoUrl,
  samlCert,
  setSamlCert,
  spCert,
  setSpCert,
  spPrivateKey,
  setSpPrivateKey,
  onUploadCert,
  uploadPending,
}: SamlFieldsProps) {
  return (
    <div className="flex flex-col gap-4">
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
        <div className="flex flex-col gap-4 rounded-lg border p-4">
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
            disabled={uploadPending}
            onClick={onUploadCert}
          >
            Upload SP certificate
          </Button>
        </div>
      ) : null}
    </div>
  )
}
