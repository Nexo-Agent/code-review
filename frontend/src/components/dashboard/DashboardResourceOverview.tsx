import { Link } from "@tanstack/react-router"

import type { DashboardResourcesSection } from "@/api/dashboard-types"
import { DataPanel } from "@/components/patterns/data-panel"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DEFAULT_LIST_SEARCH,
  DEFAULT_REPOSITORIES_SEARCH,
  DEFAULT_USERS_SEARCH,
} from "@/lib/pagination"

function ResourceLink({
  label,
  count,
  to,
  search,
}: {
  label: string
  count: number
  to: string
  search?: Record<string, unknown>
}) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>
        <Link to={to} search={search} className="font-medium hover:underline">
          {count}
        </Link>
      </dd>
    </div>
  )
}

export function DashboardResourceOverview({
  resources,
  loading,
  error,
}: {
  resources: DashboardResourcesSection | undefined
  loading?: boolean
  error?: boolean
}) {
  return (
    <Card className="border-border/70 flex h-full flex-col shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Resources</CardTitle>
        <CardDescription>Counts available in your current scope</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <DataPanel loading={loading} error={error} className="flex flex-1 flex-col">
          <dl className="grid gap-2">
            <ResourceLink
              label="Teams"
              count={resources?.teams ?? 0}
              to="/teams"
              search={DEFAULT_LIST_SEARCH}
            />
            <ResourceLink
              label="Repositories"
              count={resources?.repositories ?? 0}
              to="/repositories"
              search={DEFAULT_REPOSITORIES_SEARCH}
            />
            {resources?.users != null ? (
              <ResourceLink
                label="Users"
                count={resources.users}
                to="/users"
                search={DEFAULT_USERS_SEARCH}
              />
            ) : null}
            {resources?.llm_providers != null ? (
              <ResourceLink
                label="LLM providers"
                count={resources.llm_providers}
                to="/llm-providers"
                search={DEFAULT_LIST_SEARCH}
              />
            ) : null}
          </dl>
        </DataPanel>
      </CardContent>
    </Card>
  )
}
