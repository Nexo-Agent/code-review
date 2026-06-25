export interface HealthResponse {
  status: string
  db: string
  version: string
}

export interface ReviewFinding {
  id: string
  severity: string
  file_path: string | null
  line_start: number | null
  line_end: number | null
  title: string
  body: string
  created_at: string
}

export interface Review {
  id: string
  provider: string
  repo_full_name: string
  pr_number: number
  pr_title: string
  head_sha: string
  status: string
  delivery_id: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  findings_count: number
  findings: ReviewFinding[]
}

export interface ReviewList {
  items: Review[]
  total: number
}
