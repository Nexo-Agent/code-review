import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/reviews", label: "Reviews" },
  { to: "/settings", label: "Settings" },
  { to: "/examples", label: "Examples" },
] as const

export function AppShell({
  children,
  title,
}: {
  children: ReactNode
  title?: string
}) {
  return (
    <div className="bg-background min-h-svh">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
          <span className="font-semibold">Code Review</span>
          <nav className="flex items-center gap-4 text-sm">
            {navItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="text-muted-foreground hover:text-foreground transition-colors"
                activeProps={{
                  className: cn("text-foreground font-medium"),
                }}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        {title ? <h1 className="mb-6 text-2xl font-semibold">{title}</h1> : null}
        {children}
      </main>
    </div>
  )
}
