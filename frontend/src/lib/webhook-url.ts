import { apiBaseUrl } from "@/api/client"

export function webhookFullUrl(path: string) {
  return `${apiBaseUrl()}${path}`
}
