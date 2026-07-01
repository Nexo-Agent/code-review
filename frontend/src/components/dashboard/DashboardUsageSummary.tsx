import { Link } from "@tanstack/react-router"

import type { DashboardUsageSection } from "@/api/dashboard-types"
import { DataPanel } from "@/components/patterns/data-panel"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { DEFAULT_USAGE_SEARCH } from "@/lib/pagination"

function formatTokens(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  return value.toLocaleString()
}

function formatWindow(start: string, end: string): string {
  return `${new Date(start).toLocaleDateString()} – ${new Date(end).toLocaleDateString()}`
}

export function DashboardUsageSummary({
  usage,
  loading,
  error,
}: {
  usage: DashboardUsageSection | null | undefined
  loading?: boolean
  error?: boolean
}) {
  return (
    <Card className="border-border/70 flex h-full flex-col shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-medium">Usage (30 days)</CardTitle>
            <CardDescription>
              {usage
                ? formatWindow(usage.window_start, usage.window_end)
                : "LLM token and review usage"}
            </CardDescription>
          </div>
          <Link
            to="/usage"
            search={DEFAULT_USAGE_SEARCH}
            className="text-muted-foreground hover:text-foreground shrink-0 text-xs font-medium"
          >
            View usage
          </Link>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <DataPanel
          loading={loading}
          error={error}
          className="flex min-h-0 flex-1 flex-col"
        >
          {!usage ? (
            <p className="text-muted-foreground text-sm">
              Usage data is not available for your role.
            </p>
          ) : (
            <div className="grid h-full flex-1 gap-3 sm:grid-cols-3">
              <UsageMetricCard
                label="Total tokens"
                value={formatTokens(usage.total_tokens)}
              />
              <UsageMetricCard
                label="LLM calls"
                value={usage.llm_call_count.toLocaleString()}
              />
              <UsageMetricCard
                label="Reviews"
                value={usage.review_count.toLocaleString()}
              />
            </div>
          )}
        </DataPanel>
      </CardContent>
    </Card>
  )
}

function UsageMetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex h-full min-h-24 flex-col justify-center rounded-lg border border-border/70 px-4 py-3">
      <p className="text-muted-foreground text-[11px] font-semibold tracking-[0.16em] uppercase">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
    </div>
  )
}
