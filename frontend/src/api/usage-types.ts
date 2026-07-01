export interface UsageSummary {
  total_tokens: number
  input_tokens: number
  output_tokens: number
  llm_call_count: number
  review_count: number
  window_start: string
  window_end: string
}

export interface UsageHistoryPoint {
  window_start: string
  window_end: string
  metric_value_num: number
  sample_size: number
}

export interface UsageHistory {
  metric_key: string
  window_start: string
  window_end: string
  points: UsageHistoryPoint[]
}

export interface UsageBreakdownItem {
  dimension_id: string
  dimension_label: string
  review_count: number
  llm_call_count: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  percent_of_total: number
}

export interface UsageBreakdown {
  group_by: string
  window_start: string
  window_end: string
  items: UsageBreakdownItem[]
}

export type UsageMetricKey =
  | "total_tokens"
  | "input_tokens"
  | "output_tokens"
  | "llm_call_count"
  | "review_count"

export interface UsageFilters {
  team_id?: string
  repo_integration_id?: string
  git_provider?: string
  llm_provider_id?: string
  start?: string
  end?: string
  days?: number
}
