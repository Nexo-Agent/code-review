export interface InstallStatus {
  setup_required: boolean
}

export interface InstallBootstrapPayload {
  username: string
  password: string
  email?: string | null
  name?: string | null
}

export interface LocalLoginPayload {
  username: string
  password: string
}
