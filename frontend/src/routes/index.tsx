import { createFileRoute, Link } from "@tanstack/react-router"

import { AppShell } from "@/components/layout/AppShell"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useHealth } from "@/hooks/use-health"
import { useLlmProviders, useRepoIntegrations } from "@/hooks/use-settings"

export const Route = createFileRoute("/")({
  component: DashboardPage,
})

function DashboardPage() {
  const health = useHealth()
  const repos = useRepoIntegrations()
  const llmProviders = useLlmProviders()

  return (
    <AppShell title="Dashboard">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">System status</CardTitle>
            <CardDescription>API and database connectivity</CardDescription>
          </CardHeader>
          <CardContent>
            {health.isPending ? (
              <div className="flex flex-col gap-1.5">
                <Skeleton className="h-3.5 w-32" />
                <Skeleton className="h-3.5 w-48" />
              </div>
            ) : health.isError ? (
              <p className="text-destructive text-sm">
                Failed to reach API. Start backend with{" "}
                <code className="text-xs">make dev</code>.
              </p>
            ) : (
              <dl className="grid gap-1.5 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd className="font-medium">{health.data.status}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Database</dt>
                  <dd className="font-medium">{health.data.db}</dd>
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
            <CardTitle className="text-sm">Overview</CardTitle>
            <CardDescription>Configured resources</CardDescription>
          </CardHeader>
          <CardContent>
            {repos.isPending || llmProviders.isPending ? (
              <div className="flex flex-col gap-1.5">
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
                      className="font-medium hover:underline"
                    >
                      {repos.data?.length ?? 0}
                    </Link>
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">LLM providers</dt>
                  <dd>
                    <Link
                      to="/llm-providers"
                      className="font-medium hover:underline"
                    >
                      {llmProviders.data?.length ?? 0}
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
