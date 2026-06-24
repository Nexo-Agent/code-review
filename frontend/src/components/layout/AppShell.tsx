import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

const navItems = [
  { to: "/", label: "Dashboard", exact: true },
  { to: "/repositories", label: "Repository", exact: false },
  { to: "/llm-providers", label: "LLM Provider", exact: false },
] as const

export function AppShell({
  children,
  title,
}: {
  children: ReactNode
  title?: string
}) {
  return (
    <div className="bg-background flex min-h-svh">
      <aside className="bg-card flex w-56 shrink-0 flex-col border-r">
        <div className="flex h-14 items-center border-b px-4">
          <span className="font-semibold tracking-tight">Nexo Co-Review</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "text-muted-foreground hover:bg-accent hover:text-accent-foreground rounded-md px-3 py-2 text-sm transition-colors",
              )}
              activeOptions={{ exact: item.exact }}
              activeProps={{
                className: cn(
                  "bg-accent text-accent-foreground font-medium",
                ),
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <main className="flex-1 px-8 py-8">
          {title ? (
            <h1 className="mb-6 text-2xl font-semibold tracking-tight">{title}</h1>
          ) : null}
          {children}
        </main>
      </div>
    </div>
  )
}
