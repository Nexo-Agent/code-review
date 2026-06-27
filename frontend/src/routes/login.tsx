import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import { Field } from "@/components/forms/Field"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { loginUrl } from "@/hooks/use-auth"
import { useLocalLogin } from "@/hooks/use-install"
import { usePublicIdentityProvider } from "@/hooks/use-identity-provider"

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>) => ({
    return_to: typeof search.return_to === "string" ? search.return_to : undefined,
    error: typeof search.error === "string" ? search.error : undefined,
  }),
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const { return_to: returnTo, error } = Route.useSearch()
  const idp = usePublicIdentityProvider()
  const localLogin = useLocalLogin()

  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [showLocal, setShowLocal] = useState(false)

  const ssoEnabled = idp.data?.enabled ?? false
  const buttonLabel =
    ssoEnabled && idp.data?.display_name
      ? `Continue with ${idp.data.display_name}`
      : "Continue with SSO"

  async function handleLocalSubmit(event: React.FormEvent) {
    event.preventDefault()
    try {
      await localLogin.mutateAsync({ username, password })
      void navigate({ to: returnTo ?? "/" })
    } catch {
      toast.error("Invalid username or password")
    }
  }

  return (
    <div className="bg-background flex min-h-svh items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-lg font-semibold">Sign in to Cogito Review</h1>
          {error === "idp_not_configured" ? (
            <p className="text-destructive text-sm">
              SSO is not configured. Sign in with your local administrator account.
            </p>
          ) : (
            <p className="text-muted-foreground text-sm">
              Use SSO or your local administrator account.
            </p>
          )}
        </div>

        {ssoEnabled ? (
          <Button asChild className="w-full">
            <a href={loginUrl(returnTo ?? "/")}>{buttonLabel}</a>
          </Button>
        ) : null}

        {showLocal || !ssoEnabled ? (
          <form className="space-y-4" onSubmit={handleLocalSubmit}>
            <Field label="Username">
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </Field>
            <Field label="Password">
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>
            <Button
              type="submit"
              className="w-full"
              variant={ssoEnabled ? "outline" : "default"}
              disabled={localLogin.isPending}
            >
              Sign in locally
            </Button>
          </form>
        ) : (
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => setShowLocal(true)}
          >
            Local administrator sign-in
          </Button>
        )}
      </div>
    </div>
  )
}
