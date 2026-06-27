import type { UserList } from "@/api/user-types"
import { DEFAULT_PAGE_SIZE } from "@/lib/pagination"
import { usePaginatedList } from "@/hooks/use-paginated-list"

export { DEFAULT_PAGE_SIZE as PAGE_SIZE }

export function useUsersPage(params: { page: number; q: string }) {
  const query = params.q.trim()
  return usePaginatedList<UserList["items"][number]>({
    queryKey: ["users", query],
    path: "/users",
    page: params.page,
    filters: query ? { q: query } : undefined,
  })
}
