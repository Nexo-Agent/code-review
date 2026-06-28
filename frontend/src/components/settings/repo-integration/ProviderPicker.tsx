import { ProviderLogo } from "@/components/settings/repo-integration/ProviderLogo"
import {
  GIT_PROVIDERS,
  type GitProviderPickerId,
} from "@/components/settings/repo-integration/providers"
import { cn } from "@/lib/utils"

type ProviderPickerProps = {
  onSelect: (providerId: GitProviderPickerId) => void
}

export function ProviderPicker({ onSelect }: ProviderPickerProps) {
  return (
    <div className="grid grid-cols-4 gap-2.5 px-6 py-4">
      {GIT_PROVIDERS.map((provider) => (
        <ProviderCard
          key={provider.id}
          providerId={provider.id}
          label={provider.label}
          disabled={provider.disabled}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}

type ProviderCardProps = {
  providerId: GitProviderPickerId
  label: string
  disabled?: boolean
  onSelect: (providerId: GitProviderPickerId) => void
}

function ProviderCard({
  providerId,
  label,
  disabled,
  onSelect,
}: ProviderCardProps) {
  const className = cn(
    "bg-card group flex aspect-square w-full flex-col items-center justify-center gap-1.5 rounded-lg border p-2 text-center",
    disabled
      ? "cursor-not-allowed opacity-50"
      : "hover:bg-accent/40 focus-visible:ring-ring transition-colors focus-visible:ring-2 focus-visible:outline-none",
  )

  const content = (
    <>
      <ProviderLogo
        providerId={providerId}
        className={cn(
          "size-10",
          !disabled && "transition-transform group-hover:scale-105",
        )}
      />
      <span className="text-muted-foreground line-clamp-2 text-[10px] leading-tight font-medium">
        {disabled ? `${label} (soon)` : label}
      </span>
    </>
  )

  if (disabled) {
    return <div className={className}>{content}</div>
  }

  return (
    <button type="button" onClick={() => onSelect(providerId)} className={className}>
      {content}
    </button>
  )
}
