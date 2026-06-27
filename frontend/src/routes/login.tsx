import { createFileRoute } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { loginUrl } from "@/hooks/use-auth"

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>) => ({
    return_to: typeof search.return_to === "string" ? search.return_to : undefined,
  }),
  component: LoginPage,
})

function LoginPage() {
  const { return_to: returnTo } = Route.useSearch()

  return (
    <div className="bg-background flex min-h-svh items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4 text-center">
        <h1 className="text-lg font-semibold">Sign in to Cogito Review</h1>
        <p className="text-muted-foreground text-sm">
          Use your organization SSO account to continue.
        </p>
        <Button asChild className="w-full">
          <a href={loginUrl(returnTo ?? "/")}>Continue with SSO</a>
        </Button>
      </div>
    </div>
  )
}
