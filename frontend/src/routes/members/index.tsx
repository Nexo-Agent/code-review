import { createFileRoute, Link } from "@tanstack/react-router"
import { useMemo, useState } from "react"

import type { OrgMember } from "@/api/team-types"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useOrgMembers } from "@/hooks/use-teams"

export const Route = createFileRoute("/members/")({
  component: MembersPage,
})

const ROLE_OPTIONS = [
  { value: "member", label: "Member" },
  { value: "viewer", label: "Viewer" },
  { value: "team_admin", label: "Team admin" },
] as const

function memberSearchText(member: OrgMember): string {
  return [
    member.user_email,
    member.user_name,
    member.team_name,
    member.role,
  ]
    .join(" ")
    .toLowerCase()
}

function MembersPage() {
  const members = useOrgMembers()
  const memberList = members.data ?? []

  const [search, setSearch] = useState("")
  const [teamFilter, setTeamFilter] = useState<string[]>([])
  const [roleFilter, setRoleFilter] = useState("all")

  const teamOptions = useMemo(() => {
    const teams = new Map<string, string>()
    for (const member of memberList) {
      teams.set(member.team_id, member.team_name)
    }
    return [...teams.entries()].toSorted((a, b) => a[1].localeCompare(b[1]))
  }, [memberList])

  const filteredMembers = useMemo(() => {
    const query = search.trim().toLowerCase()
    return memberList.filter((member) => {
      if (teamFilter.length > 0 && !teamFilter.includes(member.team_id)) {
        return false
      }
      if (roleFilter !== "all" && member.role !== roleFilter) {
        return false
      }
      if (query && !memberSearchText(member).includes(query)) {
        return false
      }
      return true
    })
  }, [memberList, search, teamFilter, roleFilter])

  const hasFilters =
    search.trim() !== "" || teamFilter.length > 0 || roleFilter !== "all"

  const description = hasFilters
    ? `${filteredMembers.length} of ${memberList.length} members`
    : `${memberList.length} member${memberList.length === 1 ? "" : "s"}`

  return (
    <AppShell title="Members" description={description}>
      <div className="mb-4 flex flex-col gap-3">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search email, name, team…"
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

          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Role" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="all">All roles</SelectItem>
                {ROLE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
      </div>

      <DataPanel loading={members.isPending} error={members.isError}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Role</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredMembers.length ? (
              filteredMembers.map((member) => (
                <TableRow key={`${member.team_id}-${member.user_id}`}>
                  <TableCell>{member.user_email}</TableCell>
                  <TableCell>{member.user_name || "—"}</TableCell>
                  <TableCell>
                    <Link
                      to="/teams/$teamId"
                      params={{ teamId: member.team_id }}
                      className="hover:underline"
                    >
                      {member.team_name}
                    </Link>
                  </TableCell>
                  <TableCell>{member.role}</TableCell>
                </TableRow>
              ))
            ) : (
              <EmptyState colSpan={4}>
                {memberList.length
                  ? "No members match your search or filters."
                  : "No members in your accessible teams yet."}
              </EmptyState>
            )}
          </TableBody>
        </Table>
      </DataPanel>
    </AppShell>
  )
}
