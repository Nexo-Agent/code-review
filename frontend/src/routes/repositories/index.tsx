import { createFileRoute, Link } from "@tanstack/react-router"
import { useEffect, useMemo, useState } from "react"

import { AppShell } from "@/components/layout/AppShell"
import { EmptyState } from "@/components/patterns/empty-state"
import { MultiSelectFilter } from "@/components/patterns/multi-select-filter"
import { PaginatedListPanel } from "@/components/patterns/paginated-list-panel"
import {
  RepoIntegrationEnabledCell,
  RepoIntegrationLlmCell,
  RepoIntegrationNameCell,
  RepoIntegrationProviderCell,
} from "@/components/repositories/RepoIntegrationListCells"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useOrgRepositoriesPage, useTeams } from "@/hooks/use-teams"
import { GIT_PROVIDER_OPTIONS } from "@/lib/settings-constants"
import { parsePageSearch } from "@/lib/pagination"

type EnabledFilter = "all" | "enabled" | "disabled"

type RepositoriesSearch = {
  page: number
  q: string
  team: string[]
  enabled: EnabledFilter
  git_provider: string
}

function parseRepositoriesSearch(
  search: Record<string, unknown>,
): RepositoriesSearch {
  const base = parsePageSearch(search)
  const teamRaw = search.team
  const team =
    typeof teamRaw === "string"
      ? teamRaw.split(",").filter(Boolean)
      : Array.isArray(teamRaw)
        ? teamRaw.filter((value): value is string => typeof value === "string")
        : []
  const enabledRaw = search.enabled
  const enabled: EnabledFilter =
    enabledRaw === "enabled" || enabledRaw === "disabled" ? enabledRaw : "all"
  const gitProvider =
    typeof search.git_provider === "string" ? search.git_provider : "all"
  return { ...base, team, enabled, git_provider: gitProvider }
}

export const Route = createFileRoute("/repositories/")({
  validateSearch: parseRepositoriesSearch,
  component: RepositoriesPage,
})

function RepositorySearchInput({
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
      placeholder="Search repositories or teams…"
      className="max-w-md"
    />
  )
}

function RepositoriesPage() {
  const navigate = Route.useNavigate()
  const { page, q, team, enabled, git_provider } = Route.useSearch()
  const teams = useTeams()
  const repositories = useOrgRepositoriesPage({
    page,
    q,
    team_id: team,
    enabled,
    git_provider,
  })

  const teamOptions = useMemo(
    () =>
      (teams.data?.items ?? []).map((row) => ({
        value: row.id,
        label: row.name,
      })),
    [teams.data?.items],
  )

  const total = repositories.data?.total ?? 0
  const hasFilters =
    q.trim() !== "" ||
    team.length > 0 ||
    enabled !== "all" ||
    git_provider !== "all"

  const description = hasFilters
    ? `${total} repositor${total === 1 ? "y" : "ies"} matching filters`
    : `${total} repositor${total === 1 ? "y" : "ies"}`

  function goToPage(nextPage: number) {
    void navigate({ search: { page: nextPage, q, team, enabled, git_provider } })
  }

  function updateFilters(
    patch: Partial<Pick<RepositoriesSearch, "team" | "enabled" | "git_provider">>,
  ) {
    void navigate({
      search: {
        page: 1,
        q,
        team: patch.team ?? team,
        enabled: patch.enabled ?? enabled,
        git_provider: patch.git_provider ?? git_provider,
      },
    })
  }

  return (
    <AppShell title="Repositories" description={description}>
      <div className="mb-4 flex flex-col gap-3">
        <RepositorySearchInput
          key={q}
          q={q}
          onQueryChange={(trimmed) => {
            void navigate({
              search: { page: 1, q: trimmed, team, enabled, git_provider },
              replace: true,
            })
          }}
        />
        <div className="flex flex-wrap gap-2">
          <MultiSelectFilter
            options={teamOptions}
            selected={team}
            onSelectedChange={(next) => updateFilters({ team: next })}
            emptyLabel="All teams"
            searchPlaceholder="Search teams…"
            className="w-44"
          />

          <Select
            value={enabled}
            onValueChange={(value) =>
              updateFilters({ enabled: value as EnabledFilter })
            }
          >
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="all">All status</SelectItem>
                <SelectItem value="enabled">Enabled</SelectItem>
                <SelectItem value="disabled">Disabled</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>

          <Select
            value={git_provider}
            onValueChange={(value) => updateFilters({ git_provider: value })}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Provider" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="all">All providers</SelectItem>
                {GIT_PROVIDER_OPTIONS.filter(
                  (option) => !("disabled" in option && option.disabled),
                ).map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
      </div>

      <PaginatedListPanel
        query={repositories}
        page={page}
        onPageChange={goToPage}
      >
        {(repoList) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Repository</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Team</TableHead>
                <TableHead>LLM</TableHead>
                <TableHead className="w-32 text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {repoList.length ? (
                repoList.map((repo) => (
                  <TableRow key={repo.id}>
                    <TableCell>
                      <RepoIntegrationNameCell
                        repo={repo}
                        teamId={repo.team_id}
                      />
                    </TableCell>
                    <TableCell>
                      <RepoIntegrationProviderCell repo={repo} />
                    </TableCell>
                    <TableCell>
                      <Link
                        to="/teams/$teamId"
                        params={{ teamId: repo.team_id }}
                        className="text-muted-foreground hover:underline"
                      >
                        {repo.team_name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <RepoIntegrationLlmCell repo={repo} />
                    </TableCell>
                    <TableCell>
                      <RepoIntegrationEnabledCell repo={repo} />
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <EmptyState colSpan={5}>
                  {hasFilters
                    ? "No repositories match your search or filters."
                    : "No repositories in your accessible teams yet."}
                </EmptyState>
              )}
            </TableBody>
          </Table>
        )}
      </PaginatedListPanel>
    </AppShell>
  )
}
