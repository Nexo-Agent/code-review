import { createFileRoute } from "@tanstack/react-router"

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

export const Route = createFileRoute("/")({
  component: DashboardPage,
})

function DashboardPage() {
  const health = useHealth()

  return (
    <AppShell title="Dashboard">
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>System status</CardTitle>
          <CardDescription>API and database connectivity</CardDescription>
        </CardHeader>
        <CardContent>
          {health.isPending ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-48" />
            </div>
          ) : health.isError ? (
            <p className="text-destructive text-sm">
              Failed to reach API. Start backend with{" "}
              <code className="text-xs">make dev-api</code>.
            </p>
          ) : (
            <dl className="grid gap-2 text-sm">
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
    </AppShell>
  )
}
