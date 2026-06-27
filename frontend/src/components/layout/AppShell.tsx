import { Link } from "@tanstack/react-router"
import { ChevronUp } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useLogout, useMe } from "@/hooks/use-auth"
import { cn } from "@/lib/utils"

const baseNavItems = [
  { to: "/", label: "Dashboard", exact: true },
  { to: "/teams", label: "Teams", exact: false },
  { to: "/repositories", label: "Repositories", exact: false },
  { to: "/members", label: "Members", exact: false },
  { to: "/reviews", label: "Reviews", exact: false },
] as const

export function AppShell({
  children,
  title,
  description,
  actions,
  mainClassName,
}: {
  children: ReactNode
  title?: string
  description?: string
  actions?: ReactNode
  mainClassName?: string
}) {
  const me = useMe()
  const logout = useLogout()
  const showHeader = title || description || actions
  const isOrgAdmin = me.data?.user.is_org_admin ?? false

  const navItems = isOrgAdmin
    ? [...baseNavItems, { to: "/llm-providers", label: "LLM Providers", exact: false }]
    : baseNavItems

  return (
    <div className="bg-background flex h-svh overflow-hidden">
      <aside className="bg-muted/30 flex w-52 shrink-0 flex-col">
        <div className="flex h-11 items-center px-3">
          <span className="truncate text-sm font-semibold tracking-tight">
            Cogito Review
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
        <div className="border-t p-2">
          {me.data ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="w-full justify-between gap-2 px-2.5 font-medium"
                >
                  <span className="truncate">
                    {me.data.user.name || me.data.user.email}
                  </span>
                  <ChevronUp className="text-muted-foreground shrink-0" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                side="top"
                align="start"
                className="w-(--radix-dropdown-menu-trigger-width)"
              >
                <DropdownMenuGroup>
                  <DropdownMenuItem
                    disabled={logout.isPending}
                    onClick={() => logout.mutate()}
                  >
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : null}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {showHeader ? (
          <header className="bg-background flex shrink-0 items-start gap-3 border-b border-border/50 px-4 py-3">
            <div className="min-w-0 flex-1">
              {title ? (
                <h1 className="line-clamp-2 text-base leading-snug font-semibold tracking-tight">
                  {title}
                </h1>
              ) : null}
              {description ? (
                <p className="text-muted-foreground mt-0.5 truncate text-xs">
                  {description}
                </p>
              ) : null}
            </div>
            {actions ? (
              <div className="flex shrink-0 items-center gap-2 pt-0.5">
                {actions}
              </div>
            ) : null}
          </header>
        ) : null}

        <main
          className={cn(
            "flex-1 overflow-y-auto p-4",
            mainClassName,
          )}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
