import { Outlet, createRootRouteWithContext } from "@tanstack/react-router"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import type { QueryClient } from "@tanstack/react-query"
import { Toaster } from "sonner"

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()(
  {
    component: RootComponent,
  },
)

function RootComponent() {
  return (
    <>
      <Outlet />
      <Toaster position="top-right" />
      {import.meta.env.DEV ? <ReactQueryDevtools initialIsOpen={false} /> : null}
    </>
  )
}
