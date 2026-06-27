import { Outlet, createRootRouteWithContext, redirect } from "@tanstack/react-router"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import type { QueryClient } from "@tanstack/react-query"
import { Toaster } from "sonner"

import type { MeResponse } from "@/api/auth-types"
import { api } from "@/api/client"
import type { InstallStatus } from "@/api/install-types"
import { defaultLoginSearch } from "@/hooks/use-auth"

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  beforeLoad: async ({ location }) => {
    const pathname = location.pathname
    const isInstall = pathname === "/install"
    const isLogin = pathname === "/login"

    let setupRequired = false
    try {
      const status = await api<InstallStatus>("/install/status")
      setupRequired = status.setup_required
    } catch {
      // API unavailable — treat as setup complete to avoid blocking the app
    }

    if (setupRequired) {
      if (!isInstall) {
        throw redirect({ to: "/install" })
      }
      return
    }

    if (isInstall) {
      throw redirect({ to: "/login", search: defaultLoginSearch })
    }

    if (isLogin) {
      return
    }

    try {
      const me = await api<MeResponse>("/auth/me")
      return { me }
    } catch {
      throw redirect({
        to: "/login",
        search: { return_to: location.pathname, error: undefined },
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
