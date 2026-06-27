import { Link } from "@tanstack/react-router"

import { ProviderLogo } from "@/components/settings/identity-provider/ProviderLogo"
import {
  SSO_PROVIDERS,
  type SsoProviderId,
} from "@/components/settings/identity-provider/providers"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export function ProviderPicker() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-medium">Choose an identity provider</h2>
        <p className="text-muted-foreground text-sm">
          Select a provider to configure single sign-on for your organization.
          Only one provider can be active at a time.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {SSO_PROVIDERS.map((provider) => (
          <ProviderCard key={provider.id} providerId={provider.id} />
        ))}
      </div>
    </div>
  )
}

function ProviderCard({ providerId }: { providerId: SsoProviderId }) {
  const provider = SSO_PROVIDERS.find((item) => item.id === providerId)
  if (!provider) return null

  return (
    <Link
      to="/settings/identity-provider"
      search={{ setup: providerId, edit: false }}
      className={cn(
        "bg-card hover:bg-accent/40 focus-visible:ring-ring group flex aspect-square flex-col items-center justify-center gap-3 rounded-lg border p-4 text-center transition-colors focus-visible:ring-2 focus-visible:outline-none",
      )}
    >
      <ProviderLogo
        providerId={providerId}
        className="size-14 transition-transform group-hover:scale-105"
      />
      <div className="flex flex-col items-center gap-1.5">
        <span className="text-sm leading-tight font-medium">{provider.label}</span>
        <Badge variant="muted">
          {provider.protocol === "oidc" ? "OIDC" : "SAML"}
        </Badge>
      </div>
    </Link>
  )
}
