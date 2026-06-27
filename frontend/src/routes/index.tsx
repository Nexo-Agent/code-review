import { createFileRoute, Link } from "@tanstack/react-router"

import { AppShell } from "@/components/layout/AppShell"
import { CodeHint, InlineError } from "@/components/patterns/inline-error"
import { HealthBadge } from "@/components/patterns/status-badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useHealth } from "@/hooks/use-health"
import { useReviews } from "@/hooks/use-reviews"
import { useLlmProviders, useRepoIntegrations } from "@/hooks/use-settings"
import {
  DEFAULT_LIST_SEARCH,
  DEFAULT_REPOSITORIES_SEARCH,
  DEFAULT_REVIEWS_SEARCH,
} from "@/lib/pagination"

export const Route = createFileRoute("/")({
  component: DashboardPage,
})

function DashboardPage() {
  const health = useHealth()
  const repos = useRepoIntegrations()
  const llmProviders = useLlmProviders()
  const reviews = useReviews()

  return (
    <AppShell title="Dashboard">
      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">System status</CardTitle>
            <CardDescription>API and database connectivity</CardDescription>
          </CardHeader>
          <CardContent>
            {health.isPending ? (
              <div className="flex flex-col gap-1.5">
                <Skeleton className="h-3.5 w-32" />
                <Skeleton className="h-3.5 w-48" />
              </div>
            ) : health.isError ? (
              <InlineError
                message="Failed to reach API. Start backend with"
                hint={<CodeHint>make dev</CodeHint>}
              />
            ) : (
              <dl className="grid gap-1.5 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>
                    <HealthBadge value={health.data.status} />
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Database</dt>
                  <dd>
                    <HealthBadge value={health.data.db} />
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Version</dt>
                  <dd className="font-medium">{health.data.version}</dd>
                </div>
              </dl>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Overview</CardTitle>
            <CardDescription>Configured resources</CardDescription>
          </CardHeader>
          <CardContent>
            {repos.isPending || llmProviders.isPending || reviews.isPending ? (
              <div className="flex flex-col gap-1.5">
                <Skeleton className="h-3.5 w-32" />
                <Skeleton className="h-3.5 w-32" />
                <Skeleton className="h-3.5 w-32" />
              </div>
            ) : (
              <dl className="grid gap-1.5 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Repositories</dt>
                  <dd>
                    <Link
                      to="/repositories"
                      search={DEFAULT_REPOSITORIES_SEARCH}
                      className="font-medium hover:underline"
                    >
                      {repos.data?.total ?? 0}
                    </Link>
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Reviews</dt>
                  <dd>
                    <Link
                      to="/reviews"
                      search={DEFAULT_REVIEWS_SEARCH}
                      className="font-medium hover:underline"
                    >
                      {reviews.data?.total ?? 0}
                    </Link>
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">LLM providers</dt>
                  <dd>
                    <Link
                      to="/llm-providers"
                      search={DEFAULT_LIST_SEARCH}
                      className="font-medium hover:underline"
                    >
                      {llmProviders.data?.total ?? 0}
                    </Link>
                  </dd>
                </div>
              </dl>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
