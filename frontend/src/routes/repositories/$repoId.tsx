import { createFileRoute, redirect } from "@tanstack/react-router"

import { DEFAULT_LIST_SEARCH } from "@/lib/pagination"

export const Route = createFileRoute("/repositories/$repoId")({
  beforeLoad: () => {
    throw redirect({ to: "/teams", search: DEFAULT_LIST_SEARCH })
  },
})
