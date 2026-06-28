import type { LlmProviderCreate } from "@/api/settings-types"

export type LlmProviderPresetId =
  | "google"
  | "anthropic"
  | "openai"
  | "deepseek"
  | "mistral"
  | "cohere"
  | "openrouter"
  | "togetherai"
  | "fireworks-ai"
  | "groq"
  | "deepinfra"
  | "moonshotai"
  | "moonshotai-cn"
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
    id: "mistral",
    label: "Mistral AI",
    description: "Mistral models via the Mistral API.",
    provider_id: "mistral",
    defaultBaseUrl: "https://api.mistral.ai/v1",
    modelPlaceholder: "mistral-large-latest",
    defaultModel: "mistral-large-latest",
    showBaseUrl: false,
  },
  {
    id: "cohere",
    label: "Cohere",
    description: "Cohere models via the OpenAI-compatible Compatibility API.",
    provider_id: "cohere",
    defaultBaseUrl: "https://api.cohere.ai/compatibility/v1",
    modelPlaceholder: "command-a-03-2025",
    defaultModel: "command-a-03-2025",
    showBaseUrl: false,
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    description: "Multi-model routing via the OpenRouter API.",
    provider_id: "openrouter",
    defaultBaseUrl: "https://openrouter.ai/api/v1",
    modelPlaceholder: "anthropic/claude-sonnet-4",
    defaultModel: "anthropic/claude-sonnet-4",
    showBaseUrl: false,
  },
  {
    id: "togetherai",
    label: "Together AI",
    description: "Open models hosted on Together AI.",
    provider_id: "togetherai",
    defaultBaseUrl: "https://api.together.xyz/v1",
    modelPlaceholder: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    defaultModel: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    showBaseUrl: false,
  },
  {
    id: "fireworks-ai",
    label: "Fireworks AI",
    description: "Fast inference for open models on Fireworks AI.",
    provider_id: "fireworks-ai",
    defaultBaseUrl: "https://api.fireworks.ai/inference/v1",
    modelPlaceholder: "accounts/fireworks/models/llama-v3p3-70b-instruct",
    defaultModel: "accounts/fireworks/models/llama-v3p3-70b-instruct",
    showBaseUrl: false,
  },
  {
    id: "groq",
    label: "Groq",
    description: "Ultra-fast inference via the Groq API.",
    provider_id: "groq",
    defaultBaseUrl: "https://api.groq.com/openai/v1",
    modelPlaceholder: "llama-3.3-70b-versatile",
    defaultModel: "llama-3.3-70b-versatile",
    showBaseUrl: false,
  },
  {
    id: "deepinfra",
    label: "DeepInfra",
    description: "Hosted open models via the DeepInfra API.",
    provider_id: "deepinfra",
    defaultBaseUrl: "https://api.deepinfra.com/v1/openai",
    modelPlaceholder: "meta-llama/Llama-3.3-70B-Instruct",
    defaultModel: "meta-llama/Llama-3.3-70B-Instruct",
    showBaseUrl: false,
  },
  {
    id: "moonshotai",
    label: "Moonshot AI",
    description: "Kimi models via the international Moonshot API.",
    provider_id: "moonshotai",
    defaultBaseUrl: "https://api.moonshot.ai/v1",
    modelPlaceholder: "kimi-k2.5",
    defaultModel: "kimi-k2.5",
    showBaseUrl: false,
  },
  {
    id: "moonshotai-cn",
    label: "Moonshot AI (China)",
    description: "Kimi models via the China Moonshot API (api.moonshot.cn).",
    provider_id: "moonshotai-cn",
    defaultBaseUrl: "https://api.moonshot.cn/v1",
    modelPlaceholder: "kimi-k2.5",
    defaultModel: "kimi-k2.5",
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
