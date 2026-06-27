import type { SsoProviderId } from "@/components/settings/identity-provider/providers"
import { cn } from "@/lib/utils"

type ProviderLogoProps = {
  providerId: SsoProviderId
  className?: string
}

export function ProviderLogo({ providerId, className }: ProviderLogoProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center",
        className,
      )}
      aria-hidden
    >
      {providerId === "google" ? <GoogleLogo /> : null}
      {providerId === "entra" ? <EntraLogo /> : null}
      {providerId === "okta" ? <OktaLogo /> : null}
      {providerId === "keycloak" ? <KeycloakLogo /> : null}
      {providerId === "auth0" ? <Auth0Logo /> : null}
      {providerId === "custom" ? <CustomOidcLogo /> : null}
      {providerId === "saml" ? <SamlLogo /> : null}
    </span>
  )
}

function GoogleLogo() {
  return (
    <svg viewBox="0 0 48 48" className="size-full" role="img">
      <path
        fill="#FFC107"
        d="M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.223 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C33.64 6.053 29.082 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
      />
      <path
        fill="#FF3D00"
        d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C33.64 6.053 29.082 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.099 0 9.748-1.947 13.243-5.118l-6.109-5.094C29.223 36 24.818 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
      />
      <path
        fill="#1976D2"
        d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.788l.003-.002 6.109 5.094C36.737 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"
      />
    </svg>
  )
}

function EntraLogo() {
  return (
    <svg viewBox="0 0 48 48" className="size-full" role="img">
      <rect x="4" y="4" width="18" height="18" fill="#F25022" />
      <rect x="26" y="4" width="18" height="18" fill="#7FBA00" />
      <rect x="4" y="26" width="18" height="18" fill="#00A4EF" />
      <rect x="26" y="26" width="18" height="18" fill="#FFB900" />
    </svg>
  )
}

function OktaLogo() {
  return (
    <svg viewBox="0 0 48 48" className="size-full" role="img">
      <circle cx="24" cy="24" r="20" fill="#007DC1" />
      <circle cx="24" cy="24" r="10" fill="white" />
    </svg>
  )
}

function KeycloakLogo() {
  return (
    <svg viewBox="0 0 48 48" className="size-full" role="img">
      <rect width="48" height="48" rx="10" fill="#4D4D4D" />
      <path
        fill="#00B4E6"
        d="M12 30c0-6.627 5.373-12 12-12s12 5.373 12 12"
      />
      <circle cx="24" cy="18" r="6" fill="#EDEDED" />
      <path fill="#EDEDED" d="M18 32h12v4H18z" />
    </svg>
  )
}

function Auth0Logo() {
  return (
    <svg viewBox="0 0 48 48" className="size-full" role="img">
      <path fill="#EB5424" d="M24 6 8 38h8l8-16 8 16h8L24 6z" />
    </svg>
  )
}

function CustomOidcLogo() {
  return (
    <svg viewBox="0 0 48 48" className="size-full" role="img">
      <rect width="48" height="48" rx="10" className="fill-muted" />
      <path
        className="stroke-foreground"
        strokeWidth="2.5"
        fill="none"
        d="M24 10c-5.523 0-10 3.582-10 8s4.477 8 10 8 10 3.582 10 8-4.477 8-10 8"
      />
      <circle cx="24" cy="18" r="3" className="fill-foreground" />
    </svg>
  )
}

function SamlLogo() {
  return (
    <svg viewBox="0 0 48 48" className="size-full" role="img">
      <rect width="48" height="48" rx="10" className="fill-muted" />
      <path
        className="fill-foreground"
        d="M24 10a8 8 0 0 0-8 8v4h-2a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h20a2 2 0 0 0 2-2V24a2 2 0 0 0-2-2h-2v-4a8 8 0 0 0-8-8zm0 4a4 4 0 0 1 4 4v4H20v-4a4 4 0 0 1 4-4z"
      />
    </svg>
  )
}
