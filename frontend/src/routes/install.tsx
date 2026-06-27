import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"

import { api } from "@/api/client"
import { Field } from "@/components/forms/Field"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useInstallBootstrap, useInstallStatus } from "@/hooks/use-install"
import { defaultLoginSearch } from "@/hooks/use-auth"

export const Route = createFileRoute("/install")({
  beforeLoad: async () => {
    const status = await api<{ setup_required: boolean }>("/install/status")
    if (!status.setup_required) {
      throw redirect({ to: "/login", search: defaultLoginSearch })
    }
  },
  component: InstallPage,
})

function InstallPage() {
  const navigate = useNavigate()
  const status = useInstallStatus()
  const bootstrap = useInstallBootstrap()

  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")

  if (status.data && !status.data.setup_required) {
    void navigate({ to: "/login", search: defaultLoginSearch })
    return null
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (password !== confirmPassword) {
      toast.error("Passwords do not match")
      return
    }
    if (password.length < 12) {
      toast.error("Password must be at least 12 characters")
      return
    }
    try {
      await bootstrap.mutateAsync({
        username: username.trim().toLowerCase(),
        password,
        email: email.trim() || null,
        name: name.trim() || null,
      })
      toast.success("Setup complete")
      void navigate({ to: "/" })
    } catch {
      toast.error("Setup failed. The system may already be configured.")
    }
  }

  return (
    <div className="bg-background flex min-h-svh items-center justify-center p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-lg font-semibold">Install Cogito Review</h1>
          <p className="text-muted-foreground text-sm">
            Create the initial super administrator account. This step runs once
            and cannot be repeated.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <Field label="Username">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="admin"
              required
            />
          </Field>

          <Field label="Display name (optional)">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
            />
          </Field>

          <Field label="Email (optional)">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="admin@example.com"
            />
          </Field>

          <Field label="Password">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </Field>

          <Field label="Confirm password">
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </Field>

          <Button
            type="submit"
            className="w-full"
            disabled={
              bootstrap.isPending ||
              !username.trim() ||
              !password ||
              !confirmPassword
            }
          >
            Complete setup
          </Button>
        </form>
      </div>
    </div>
  )
}
