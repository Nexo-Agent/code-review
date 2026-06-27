export type IdentityProviderProtocol = "oidc" | "saml"
export type IdentityProviderPreset =
  | "google"
  | "okta"
  | "keycloak"
  | "entra"
  | "auth0"
  | "custom"

export interface IdentityProviderPublic {
  enabled: boolean
  display_name: string
  protocol: string
}

export interface IdentityProvider {
  organization_id: string
  protocol: IdentityProviderProtocol
  preset: IdentityProviderPreset
  enabled: boolean
  display_name: string
  oidc_issuer: string | null
  oidc_client_id: string | null
  oidc_client_secret_configured: boolean
  oidc_scopes: string
  oidc_authorize_url: string | null
  oidc_token_url: string | null
  oidc_userinfo_url: string | null
  saml_idp_entity_id: string | null
  saml_idp_sso_url: string | null
  saml_idp_slo_url: string | null
  saml_idp_cert_configured: boolean
  saml_sp_entity_id: string | null
  saml_sp_acs_url: string | null
  saml_sp_cert_configured: boolean
  saml_sp_private_key_configured: boolean
  email_claim: string
  name_claim: string
  sub_claim: string
  oidc_redirect_uri: string
  saml_metadata_url: string
  created_at: string
  updated_at: string
}

export interface IdentityProviderUpsertPayload {
  protocol: IdentityProviderProtocol
  preset: IdentityProviderPreset
  enabled: boolean
  display_name?: string
  oidc_issuer?: string | null
  oidc_client_id?: string | null
  oidc_client_secret?: string | null
  clear_oidc_client_secret?: boolean
  oidc_scopes?: string
  oidc_authorize_url?: string | null
  oidc_token_url?: string | null
  oidc_userinfo_url?: string | null
  saml_idp_metadata_url?: string | null
  saml_idp_metadata_xml?: string | null
  saml_idp_entity_id?: string | null
  saml_idp_sso_url?: string | null
  saml_idp_slo_url?: string | null
  saml_idp_cert?: string | null
  email_claim?: string
  name_claim?: string
  sub_claim?: string
  preset_tenant_id?: string | null
  preset_domain?: string | null
  preset_base_url?: string | null
  preset_realm?: string | null
}

export interface SamlSpCertUploadPayload {
  sp_cert: string
  sp_private_key: string
}
