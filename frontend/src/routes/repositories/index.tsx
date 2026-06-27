import { createFileRoute, Link } from "@tanstack/react-router"
import { useMemo, useState } from "react"

import type { OrgRepository } from "@/api/team-types"
import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { EmptyState } from "@/components/patterns/empty-state"
import { MultiSelectFilter } from "@/components/patterns/multi-select-filter"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useOrgRepositories } from "@/hooks/use-teams"
import { GIT_PROVIDER_OPTIONS } from "@/lib/settings-constants"

export const Route = createFileRoute("/repositories/")({
  component: RepositoriesPage,
})

type EnabledFilter = "all" | "enabled" | "disabled"

function repoSearchText(repo: OrgRepository): string {
  return [
    repo.repo_full_name,
    repo.name,
    repo.team_name,
    repo.project_name,
    repo.llm_provider_name ?? "Org default",
    repo.git_provider,
  ]
    .join(" ")
    .toLowerCase()
}

function RepositoriesPage() {
  const repositories = useOrgRepositories()
  const repoList = repositories.data ?? []

  const [search, setSearch] = useState("")
  const [teamFilter, setTeamFilter] = useState<string[]>([])
  const [enabledFilter, setEnabledFilter] = useState<EnabledFilter>("all")
  const [gitProviderFilter, setGitProviderFilter] = useState("all")

  const teamOptions = useMemo(() => {
    const teams = new Map<string, string>()
    for (const repo of repoList) {
      teams.set(repo.team_id, repo.team_name)
    }
    return [...teams.entries()].toSorted((a, b) => a[1].localeCompare(b[1]))
  }, [repoList])

  const filteredRepos = useMemo(() => {
    const query = search.trim().toLowerCase()
    return repoList.filter((repo) => {
      if (teamFilter.length > 0 && !teamFilter.includes(repo.team_id)) {
        return false
      }
      if (enabledFilter === "enabled" && !repo.enabled) {
        return false
      }
      if (enabledFilter === "disabled" && repo.enabled) {
        return false
      }
      if (gitProviderFilter !== "all" && repo.git_provider !== gitProviderFilter) {
        return false
      }
      if (query && !repoSearchText(repo).includes(query)) {
        return false
      }
      return true
    })
  }, [repoList, search, teamFilter, enabledFilter, gitProviderFilter])

  const hasFilters =
    search.trim() !== "" ||
    teamFilter.length > 0 ||
    enabledFilter !== "all" ||
    gitProviderFilter !== "all"

  const description = hasFilters
    ? `${filteredRepos.length} of ${repoList.length} repositories`
    : `${repoList.length} repositor${repoList.length === 1 ? "y" : "ies"}`

  return (
    <AppShell title="Repositories" description={description}>
      <div className="mb-4 flex flex-col gap-3">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search repositories, teams, projects…"
          className="max-w-md"
        />
        <div className="flex flex-wrap gap-2">
          <MultiSelectFilter
            options={teamOptions.map(([teamId, teamName]) => ({
              value: teamId,
              label: teamName,
            }))}
            selected={teamFilter}
            onSelectedChange={setTeamFilter}
            emptyLabel="All teams"
            searchPlaceholder="Search teams…"
            className="w-44"
          />

          <Select
            value={enabledFilter}
            onValueChange={(value) => setEnabledFilter(value as EnabledFilter)}
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

          <Select value={gitProviderFilter} onValueChange={setGitProviderFilter}>
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

      <DataPanel loading={repositories.isPending} error={repositories.isError}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Repository</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>LLM</TableHead>
              <TableHead className="w-20 text-right">Enabled</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredRepos.length ? (
              filteredRepos.map((repo) => (
                <TableRow key={repo.id}>
                  <TableCell>
                    <Link
                      to="/teams/$teamId/projects/$projectId/repos/$repoId"
                      params={{
                        teamId: repo.team_id,
                        projectId: repo.project_id,
                        repoId: repo.id,
                      }}
                      className="font-medium hover:underline"
                    >
                      {repo.repo_full_name || repo.name || "All repositories"}
                    </Link>
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
                    <Link
                      to="/teams/$teamId/projects/$projectId"
                      params={{
                        teamId: repo.team_id,
                        projectId: repo.project_id,
                      }}
                      className="text-muted-foreground hover:underline"
                    >
                      {repo.project_name}
                    </Link>
                  </TableCell>
                  <TableCell>{repo.llm_provider_name ?? "Org default"}</TableCell>
                  <TableCell className="text-right">
                    <Switch checked={repo.enabled} disabled />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <EmptyState colSpan={5}>
                {repoList.length
                  ? "No repositories match your search or filters."
                  : "No repositories in your accessible teams yet."}
              </EmptyState>
            )}
          </TableBody>
        </Table>
      </DataPanel>
    </AppShell>
  )
}
