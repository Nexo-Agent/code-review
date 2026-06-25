import { Link } from "@tanstack/react-router"
import { ChevronLeft } from "lucide-react"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

const navItems = [
  { to: "/", label: "Dashboard", exact: true },
  { to: "/repositories", label: "Repositories", exact: false },
  { to: "/llm-providers", label: "LLM Providers", exact: false },
] as const

export function AppShell({
  children,
  title,
  description,
  backTo,
  actions,
}: {
  children: ReactNode
  title?: string
  description?: string
  backTo?: { to: string; label?: string }
  actions?: ReactNode
}) {
  const showHeader = title || description || backTo || actions

  return (
    <div className="bg-background flex h-svh overflow-hidden">
      <aside className="bg-card flex w-44 shrink-0 flex-col border-r">
        <div className="flex h-11 items-center border-b px-3">
          <span className="truncate text-sm font-semibold tracking-tight">
            Nexo Co-Review
          </span>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-2">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "text-muted-foreground hover:bg-accent hover:text-accent-foreground rounded-md px-2.5 py-1.5 text-sm transition-colors",
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

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {showHeader ? (
          <header className="bg-background flex h-11 shrink-0 items-center gap-2 border-b px-4">
            {backTo ? (
              <ButtonLink to={backTo.to} label={backTo.label} />
            ) : null}
            <div className="min-w-0 flex-1">
              {title ? (
                <h1 className="truncate text-base font-semibold leading-tight">
                  {title}
                </h1>
              ) : null}
              {description ? (
                <p className="text-muted-foreground truncate text-xs leading-tight">
                  {description}
                </p>
              ) : null}
            </div>
            {actions ? (
              <div className="flex shrink-0 items-center gap-2">{actions}</div>
            ) : null}
          </header>
        ) : null}

        <main className="flex-1 overflow-y-auto p-4">{children}</main>
      </div>
    </div>
  )
}

function ButtonLink({ to, label }: { to: string; label?: string }) {
  return (
    <Link
      to={to}
      className="text-muted-foreground hover:text-foreground hover:bg-accent inline-flex shrink-0 items-center gap-0.5 rounded-md px-1.5 py-1 text-xs transition-colors"
    >
      <ChevronLeft className="size-3.5" />
      {label ? <span className="hidden sm:inline">{label}</span> : null}
    </Link>
  )
}
