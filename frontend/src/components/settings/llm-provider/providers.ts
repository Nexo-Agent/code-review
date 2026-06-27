import type { LlmProviderCreate } from "@/api/settings-types"

export type LlmProviderPresetId =
  | "google"
  | "anthropic"
  | "openai"
  | "deepseek"
  | "openai-compat"

export interface LlmProviderPresetDefinition {
  id: LlmProviderPresetId
  label: string
  description: string
  provider_id: string
  defaultBaseUrl: string
  modelPlaceholder: string
  defaultModel: string
  showBaseUrl: boolean
}

export const LLM_PROVIDER_PRESETS: LlmProviderPresetDefinition[] = [
  {
    id: "openai",
    label: "OpenAI",
    description: "GPT models via the OpenAI API.",
    provider_id: "openai",
    defaultBaseUrl: "https://api.openai.com/v1",
    modelPlaceholder: "gpt-4o",
    defaultModel: "gpt-4o",
    showBaseUrl: false,
  },
  {
    id: "anthropic",
    label: "Anthropic",
    description: "Claude models via the Anthropic API.",
    provider_id: "anthropic",
    defaultBaseUrl: "https://api.anthropic.com/v1",
    modelPlaceholder: "claude-sonnet-4-20250514",
    defaultModel: "claude-sonnet-4-20250514",
    showBaseUrl: false,
  },
  {
    id: "google",
    label: "Google",
    description: "Gemini models via the Google AI OpenAI-compatible API.",
    provider_id: "google",
    defaultBaseUrl:
      "https://generativelanguage.googleapis.com/v1beta/openai/",
    modelPlaceholder: "gemini-2.0-flash",
    defaultModel: "gemini-2.0-flash",
    showBaseUrl: false,
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    description: "DeepSeek models via the DeepSeek API.",
    provider_id: "deepseek",
    defaultBaseUrl: "https://api.deepseek.com/v1",
    modelPlaceholder: "deepseek-chat",
    defaultModel: "deepseek-chat",
    showBaseUrl: false,
  },
  {
    id: "openai-compat",
    label: "OpenAI Compatible API",
    description: "Any endpoint that implements the OpenAI chat completions API.",
    provider_id: "openai-compat",
    defaultBaseUrl: "https://api.openai.com/v1",
    modelPlaceholder: "your-model-id",
    defaultModel: "",
    showBaseUrl: true,
  },
]

export function getLlmProviderPreset(
  id: LlmProviderPresetId,
): LlmProviderPresetDefinition | undefined {
  return LLM_PROVIDER_PRESETS.find((preset) => preset.id === id)
}

export function getLlmProviderPresetForProviderId(
  providerId: string,
): LlmProviderPresetDefinition | undefined {
  return LLM_PROVIDER_PRESETS.find((preset) => preset.provider_id === providerId)
}

export function llmProviderLogoId(providerId: string): LlmProviderPresetId {
  return getLlmProviderPresetForProviderId(providerId)?.id ?? "openai-compat"
}

export function llmFormFromPreset(
  preset: LlmProviderPresetDefinition,
): LlmProviderCreate {
  return {
    name: preset.label,
    provider_id: preset.provider_id,
    base_url: preset.defaultBaseUrl,
    model: preset.defaultModel,
    api_token: "",
    is_default: false,
    enabled: true,
  }
}

export function llmProviderIdOptions(current?: string) {
  const options = LLM_PROVIDER_PRESETS.map((preset) => ({
    value: preset.provider_id,
    label: preset.label,
  }))
  if (current && !options.some((option) => option.value === current)) {
    return [{ value: current, label: current }, ...options]
  }
  return options
}
