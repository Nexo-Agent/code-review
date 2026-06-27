export const DEFAULT_PAGE_SIZE = 20

export type PaginatedList<T> = {
  items: T[]
  total: number
}

export function pageToOffset(page: number, pageSize = DEFAULT_PAGE_SIZE): number {
  return (page - 1) * pageSize
}

export function totalPages(total: number, pageSize = DEFAULT_PAGE_SIZE): number {
  return Math.max(1, Math.ceil(total / pageSize))
}

export function pageRange(
  page: number,
  total: number,
  pageSize = DEFAULT_PAGE_SIZE,
): { start: number; end: number } {
  if (total === 0) {
    return { start: 0, end: 0 }
  }
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  return { start, end }
}

export function parsePageSearch(search: Record<string, unknown>): {
  page: number
  q: string
} {
  const page = Number(search.page)
  return {
    page: Number.isFinite(page) && page > 0 ? page : 1,
    q: typeof search.q === "string" ? search.q : "",
  }
}

export const DEFAULT_LIST_SEARCH = { page: 1, q: "" } as const

export const DEFAULT_REVIEWS_SEARCH = {
  page: 1,
  q: "",
  status: "all",
  repo: [] as string[],
} as const

export const DEFAULT_REPOSITORIES_SEARCH = {
  page: 1,
  q: "",
  team: [] as string[],
  enabled: "all" as const,
  git_provider: "all",
} as const

export function buildListQuery(
  page: number,
  filters?: Record<string, string | string[] | undefined | null>,
  pageSize = DEFAULT_PAGE_SIZE,
): string {
  const params = new URLSearchParams({
    limit: String(pageSize),
    offset: String(pageToOffset(page, pageSize)),
  })
  if (!filters) {
    return params.toString()
  }
  for (const [key, value] of Object.entries(filters)) {
    if (value == null || value === "") {
      continue
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item) {
          params.append(key, item)
        }
      }
    } else {
      params.set(key, value)
    }
  }
  return params.toString()
}
