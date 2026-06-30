import { Link } from "@tanstack/react-router"
import {
  BarChart3,
  ChevronUp,
  FolderGit2,
  Gauge,
  GitPullRequest,
  LayoutDashboard,
  ScrollText,
  Server,
  Shield,
  Sparkles,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react"
import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useLogout, useMe } from "@/hooks/use-auth"
import { hasOrgPermission } from "@/lib/permissions"
import {
  DEFAULT_ANALYTICS_SEARCH,
  DEFAULT_LIST_SEARCH,
  DEFAULT_REPOSITORIES_SEARCH,
  DEFAULT_REVIEWS_SEARCH,
} from "@/lib/pagination"
import { cn } from "@/lib/utils"

type NavRoute =
  | "/"
  | "/analytics"
  | "/reviews"
  | "/teams"
  | "/repositories"
  | "/users"
  | "/llm-providers"
  | "/settings/identity-provider"
  | "/settings/permissions"

type NavLinkItem = {
  kind: "link"
  to: NavRoute
  label: string
  icon: LucideIcon
  exact?: boolean
  permission?: import("@/api/auth-types").ActionKey
}

type NavDisabledItem = {
  kind: "disabled"
  label: string
  icon: LucideIcon
}

type NavItem = NavLinkItem | NavDisabledItem

type NavGroup = {
  label: string
  items: NavItem[]
  permission?: import("@/api/auth-types").ActionKey
}

const dashboardItem: NavLinkItem = {
  kind: "link",
  to: "/",
  label: "Dashboard",
  icon: LayoutDashboard,
  exact: true,
}

const navGroups: NavGroup[] = [
  {
    label: "Activity",
    items: [
      {
        kind: "link",
        to: "/reviews",
        label: "Review",
        icon: GitPullRequest,
      },
      {
        kind: "link",
        to: "/analytics",
        label: "Analytics",
        icon: BarChart3,
      },
    ],
  },
  {
    label: "Resources",
    items: [
      {
        kind: "link",
        to: "/teams",
        label: "Teams",
        icon: UsersRound,
      },
      {
        kind: "link",
        to: "/repositories",
        label: "Repositories",
        icon: FolderGit2,
      },
    ],
  },
  {
    label: "Organization",
    permission: "user.read",
    items: [
      {
        kind: "link",
        to: "/users",
        label: "Users",
        icon: Users,
        permission: "user.read",
      },
      {
        kind: "link",
        to: "/llm-providers",
        label: "LLM Provider",
        icon: Sparkles,
        permission: "settings.llm.read",
      },
      {
        kind: "link",
        to: "/settings/identity-provider",
        label: "SSO",
        icon: Shield,
        permission: "settings.sso.read",
      },
      {
        kind: "link",
        to: "/settings/permissions",
        label: "Permissions",
        icon: ScrollText,
        permission: "settings.rbac.read",
      },
      { kind: "disabled", label: "Usage", icon: Gauge },
      { kind: "disabled", label: "System", icon: Server },
    ],
  },
]

const navLinkClassName =
  "text-muted-foreground hover:bg-accent hover:text-accent-foreground group flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors"

function navLinkActiveProps() {
  return {
    className: cn(
      navLinkClassName,
      "bg-accent text-accent-foreground font-medium [&_svg]:opacity-100",
    ),
  }
}

function NavItemIcon({
  icon: Icon,
  disabled = false,
}: {
  icon: LucideIcon
  disabled?: boolean
}) {
  return (
    <Icon
      className={cn(
        "size-4 shrink-0 opacity-70",
        disabled && "opacity-40",
        !disabled && "group-hover:opacity-100",
      )}
    />
  )
}

function AppNavLink({ item }: { item: NavLinkItem }) {
  const activeOptions = { exact: item.exact ?? false }
  const activeProps = navLinkActiveProps()
  const content = (
    <>
      <NavItemIcon icon={item.icon} />
      <span className="truncate">{item.label}</span>
    </>
  )

  switch (item.to) {
    case "/":
      return (
        <Link
          to="/"
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/reviews":
      return (
        <Link
          to="/reviews"
          search={DEFAULT_REVIEWS_SEARCH}
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/analytics":
      return (
        <Link
          to="/analytics"
          search={DEFAULT_ANALYTICS_SEARCH}
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/teams":
      return (
        <Link
          to="/teams"
          search={DEFAULT_LIST_SEARCH}
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/repositories":
      return (
        <Link
          to="/repositories"
          search={DEFAULT_REPOSITORIES_SEARCH}
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/users":
      return (
        <Link
          to="/users"
          search={DEFAULT_LIST_SEARCH}
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/llm-providers":
      return (
        <Link
          to="/llm-providers"
          search={DEFAULT_LIST_SEARCH}
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/settings/identity-provider":
      return (
        <Link
          to="/settings/identity-provider"
          search={{ setup: undefined, edit: false }}
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    case "/settings/permissions":
      return (
        <Link
          to="/settings/permissions"
          className={navLinkClassName}
          activeOptions={activeOptions}
          activeProps={activeProps}
        >
          {content}
        </Link>
      )
    default:
      return null
  }
}

function AppNavDisabled({ item }: { item: NavDisabledItem }) {
  return (
    <span
      aria-disabled="true"
      className="text-muted-foreground/50 flex cursor-not-allowed items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-sm"
    >
      <span className="flex min-w-0 items-center gap-2">
        <NavItemIcon icon={item.icon} disabled />
        <span className="truncate">{item.label}</span>
      </span>
      <Badge variant="secondary" className="shrink-0 px-1.5 py-0 text-[10px] font-normal">
        Soon
      </Badge>
    </span>
  )
}

function AppNavItem({ item }: { item: NavItem }) {
  if (item.kind === "disabled") {
    return <AppNavDisabled item={item} />
  }
  return <AppNavLink item={item} />
}

function AppNavGroup({ group }: { group: NavGroup }) {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-muted-foreground/80 px-2.5 pb-1.5 text-[11px] font-semibold tracking-wider uppercase">
        {group.label}
      </p>
      {group.items.map((item) => (
        <AppNavItem
          key={item.kind === "link" ? item.to : item.label}
          item={item}
        />
      ))}
    </div>
  )
}

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

  function itemVisible(item: NavItem): boolean {
    if (item.kind === "disabled") return true
    if (!item.permission) return true
    return hasOrgPermission(me.data, item.permission)
  }

  const visibleGroups = navGroups
    .filter((group) => {
      if (!group.permission) return true
      return hasOrgPermission(me.data, group.permission)
    })
    .map((group) => ({
      ...group,
      items: group.items.filter(itemVisible),
    }))
    .filter((group) => group.items.length > 0)

  return (
    <div className="bg-background flex h-svh overflow-hidden">
      <aside className="bg-sidebar flex w-60 shrink-0 flex-col border-r border-sidebar-border">
        <div className="flex h-11 shrink-0 items-center border-b border-sidebar-border px-3">
          <span className="truncate text-sm font-semibold tracking-tight">
            Cogito Review
          </span>
        </div>
        <nav className="flex flex-1 flex-col gap-5 overflow-y-auto px-2 py-3">
          <div className="flex flex-col gap-0.5">
            <AppNavLink item={dashboardItem} />
          </div>
          {visibleGroups.map((group) => (
            <AppNavGroup key={group.label} group={group} />
          ))}
        </nav>
        <div className="shrink-0 border-t border-sidebar-border p-2">
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
