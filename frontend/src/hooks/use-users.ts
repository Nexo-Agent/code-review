import { useQuery } from "@tanstack/react-query"

import { api } from "@/api/client"
import type { UserList } from "@/api/user-types"

const PAGE_SIZE = 20

export { PAGE_SIZE }

export function useUsersPage(params: { page: number; q: string }) {
  const offset = (params.page - 1) * PAGE_SIZE
  const search = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(offset),
  })
  const query = params.q.trim()
  if (query) {
    search.set("q", query)
  }

  return useQuery({
    queryKey: ["users", params.page, query],
    queryFn: () => api<UserList>(`/users?${search.toString()}`),
    placeholderData: (previous) => previous,
  })
}
