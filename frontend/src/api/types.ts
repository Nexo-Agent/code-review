export interface HealthResponse {
  status: string
  db: string
  version: string
}

export interface Example {
  id: string
  name: string
  created_at: string
}

export interface ExampleCreate {
  name: string
}
