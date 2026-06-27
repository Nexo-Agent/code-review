import { ProviderLogo } from "@/components/settings/llm-provider/ProviderLogo"
import {
  LLM_PROVIDER_PRESETS,
  type LlmProviderPresetId,
} from "@/components/settings/llm-provider/providers"
import { cn } from "@/lib/utils"

type ProviderPickerProps = {
  onSelect: (providerId: LlmProviderPresetId) => void
}

export function ProviderPicker({ onSelect }: ProviderPickerProps) {
  return (
    <div className="flex gap-2.5 px-6 py-4">
      {LLM_PROVIDER_PRESETS.map((provider) => (
        <ProviderCard
          key={provider.id}
          providerId={provider.id}
          label={provider.label}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}

type ProviderCardProps = {
  providerId: LlmProviderPresetId
  label: string
  onSelect: (providerId: LlmProviderPresetId) => void
}

function ProviderCard({ providerId, label, onSelect }: ProviderCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(providerId)}
      className={cn(
        "bg-card hover:bg-accent/40 focus-visible:ring-ring group flex size-[6.25rem] flex-col items-center justify-center gap-1.5 rounded-lg border p-2 text-center transition-colors focus-visible:ring-2 focus-visible:outline-none",
      )}
    >
      <ProviderLogo
        providerId={providerId}
        className="size-10 transition-transform group-hover:scale-105"
      />
      <span className="text-muted-foreground line-clamp-2 text-[10px] leading-tight font-medium">
        {label}
      </span>
    </button>
  )
}
