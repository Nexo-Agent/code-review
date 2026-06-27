import { createFileRoute, redirect } from "@tanstack/react-router"

import { DEFAULT_REPOSITORIES_SEARCH } from "@/lib/pagination"

export const Route = createFileRoute("/settings/")({
  beforeLoad: () => {
    throw redirect({ to: "/repositories", search: DEFAULT_REPOSITORIES_SEARCH })
  },
})
