import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/repositories/$repoId")({
  beforeLoad: () => {
    throw redirect({ to: "/teams" })
  },
})
