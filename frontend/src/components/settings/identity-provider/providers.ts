import type {
  IdentityProviderPreset,
  IdentityProviderProtocol,
} from "@/api/identity-provider-types"

export type SsoProviderId =
  | IdentityProviderPreset
  | "saml"

export interface SsoProviderDefinition {
  id: SsoProviderId
  label: string
  description: string
  protocol: IdentityProviderProtocol
  preset: IdentityProviderPreset
  defaultDisplayName: string
}

export const SSO_PROVIDERS: SsoProviderDefinition[] = [
  {
    id: "google",
    label: "Google Workspace",
    description: "Sign in with Google accounts via OpenID Connect.",
    protocol: "oidc",
    preset: "google",
    defaultDisplayName: "Google Workspace",
  },
  {
    id: "entra",
    label: "Microsoft Entra ID",
    description: "Azure AD / Entra ID single-tenant OIDC.",
    protocol: "oidc",
    preset: "entra",
    defaultDisplayName: "Microsoft Entra ID",
  },
  {
    id: "okta",
    label: "Okta",
    description: "Okta Workforce Identity Cloud OIDC.",
    protocol: "oidc",
    preset: "okta",
    defaultDisplayName: "Okta",
  },
  {
    id: "keycloak",
    label: "Keycloak",
    description: "Self-hosted Keycloak realm OIDC.",
    protocol: "oidc",
    preset: "keycloak",
    defaultDisplayName: "Keycloak",
  },
  {
    id: "auth0",
    label: "Auth0",
    description: "Auth0 tenant OIDC application.",
    protocol: "oidc",
    preset: "auth0",
    defaultDisplayName: "Auth0",
  },
  {
    id: "custom",
    label: "Custom OIDC",
    description: "Any OpenID Connect provider with a discovery issuer.",
    protocol: "oidc",
    preset: "custom",
    defaultDisplayName: "SSO",
  },
  {
    id: "saml",
    label: "SAML 2.0",
    description: "Enterprise SAML identity provider via metadata.",
    protocol: "saml",
    preset: "custom",
    defaultDisplayName: "SAML SSO",
  },
]

export function getSsoProvider(id: SsoProviderId): SsoProviderDefinition | undefined {
  return SSO_PROVIDERS.find((provider) => provider.id === id)
}

export function getSsoProviderForConfig(
  protocol: IdentityProviderProtocol,
  preset: IdentityProviderPreset,
): SsoProviderDefinition {
  if (protocol === "saml") {
    return SSO_PROVIDERS.find((p) => p.id === "saml")!
  }
  return SSO_PROVIDERS.find((p) => p.preset === preset && p.protocol === "oidc")!
}
