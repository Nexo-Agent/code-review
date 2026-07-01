import type { Review } from "@/api/types"

export interface DashboardReviewStatusCounts {
  pending: number
  running: number
  completed: number
  failed: number
}

export interface DashboardReviewsSection {
  total: number
  by_status: DashboardReviewStatusCounts
  recent: Review[]
}

export interface DashboardResourcesSection {
  teams: number
  repositories: number
  users: number | null
  llm_providers: number | null
}

export interface DashboardOnboardingStep {
  key: string
  label: string
  done: boolean
}

export interface DashboardOnboardingSection {
  steps: DashboardOnboardingStep[]
  all_complete: boolean
}

export interface DashboardAnalyticsMetric {
  metric_key: string
  metric_value_num: number | null
  numerator: number | null
  denominator: number | null
  sample_size: number | null
}

export interface DashboardAnalyticsSection {
  scope: string
  team_id: string | null
  team_name: string | null
  computed_at: string | null
  window_start: string | null
  window_end: string | null
  metrics: DashboardAnalyticsMetric[]
}

export interface DashboardUsageSection {
  total_tokens: number
  input_tokens: number
  output_tokens: number
  llm_call_count: number
  review_count: number
  window_start: string
  window_end: string
}

export interface DashboardCapabilities {
  reviews: boolean
  resources: boolean
  onboarding: boolean
  analytics: boolean
  usage: boolean
}

export interface DashboardSummary {
  capabilities: DashboardCapabilities
  reviews: DashboardReviewsSection
  resources: DashboardResourcesSection
  onboarding: DashboardOnboardingSection
  analytics: DashboardAnalyticsSection | null
  usage: DashboardUsageSection | null
}

export type DashboardOnboardingStepKey =
  | "create_team"
  | "connect_repo"
  | "configure_llm"
  | "first_review"
  | "configure_sso"
