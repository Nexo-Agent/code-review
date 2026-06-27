import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { AppShell } from "@/components/layout/AppShell"
import { EmptyState } from "@/components/patterns/empty-state"
import { PaginatedListPanel } from "@/components/patterns/paginated-list-panel"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useUsersPage } from "@/hooks/use-users"
import { parsePageSearch } from "@/lib/pagination"

export const Route = createFileRoute("/users/")({
  validateSearch: parsePageSearch,
  component: UsersPage,
})

function authSourceLabel(authSource: string): string {
  return authSource === "local" ? "Local" : "SSO"
}

function UserSearchInput({
  q,
  onQueryChange,
}: {
  q: string
  onQueryChange: (value: string) => void
}) {
  const [searchInput, setSearchInput] = useState(q)

  useEffect(() => {
    const trimmed = searchInput.trim()
    if (trimmed === q) {
      return
    }
    const timeout = window.setTimeout(() => {
      onQueryChange(trimmed)
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [searchInput, q, onQueryChange])

  return (
    <Input
      value={searchInput}
      onChange={(event) => setSearchInput(event.target.value)}
      placeholder="Search email, name, username…"
      className="max-w-md"
    />
  )
}

function UsersPage() {
  const navigate = Route.useNavigate()
  const { page, q } = Route.useSearch()
  const users = useUsersPage({ page, q })

  const total = users.data?.total ?? 0

  const description =
    total === 0
      ? "No users"
      : q.trim()
        ? `${total} user${total === 1 ? "" : "s"} matching “${q.trim()}”`
        : `${total} user${total === 1 ? "" : "s"}`

  function goToPage(nextPage: number) {
    void navigate({ search: { page: nextPage, q } })
  }

  return (
    <AppShell title="Users" description={description}>
      <div className="mb-4">
        <UserSearchInput
          key={q}
          q={q}
          onQueryChange={(trimmed) => {
            void navigate({
              search: { page: 1, q: trimmed },
              replace: true,
            })
          }}
        />
      </div>

      <PaginatedListPanel
        query={users}
        page={page}
        onPageChange={goToPage}
      >
        {(items) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Teams</TableHead>
                <TableHead>Auth</TableHead>
                <TableHead>Roles</TableHead>
                <TableHead>Joined</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length ? (
                items.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>{user.name || "—"}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {user.team_names || "—"}
                    </TableCell>
                    <TableCell>{authSourceLabel(user.auth_source)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.is_org_admin ? (
                          <Badge variant="secondary">Org admin</Badge>
                        ) : null}
                        {user.is_superuser ? (
                          <Badge variant="outline">Superuser</Badge>
                        ) : null}
                        {!user.is_org_admin && !user.is_superuser ? (
                          <span className="text-muted-foreground">—</span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap text-xs">
                      {new Date(user.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <EmptyState colSpan={6}>
                  {q.trim()
                    ? "No users match your search."
                    : "No users in the system yet."}
                </EmptyState>
              )}
            </TableBody>
          </Table>
        )}
      </PaginatedListPanel>
    </AppShell>
  )
}
