import { Outlet, createRootRouteWithContext, redirect } from "@tanstack/react-router"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import type { QueryClient } from "@tanstack/react-query"
import { Toaster } from "sonner"

import { api } from "@/api/client"
import type { MeResponse } from "@/api/auth-types"

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  beforeLoad: async ({ location }) => {
    if (location.pathname === "/login") {
      return
    }
    try {
      const me = await api<MeResponse>("/auth/me")
      return { me }
    } catch {
      throw redirect({
        to: "/login",
        search: { return_to: location.pathname },
      })
    }
  },
  component: RootComponent,
})

function RootComponent() {
  return (
    <>
      <Outlet />
      <Toaster position="bottom-right" />
      {import.meta.env.DEV ? <ReactQueryDevtools initialIsOpen={false} /> : null}
    </>
  )
}
