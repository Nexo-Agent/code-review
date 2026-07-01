import { Link } from "@tanstack/react-router"

import type { DashboardAnalyticsSection } from "@/api/dashboard-types"
import { DataPanel } from "@/components/patterns/data-panel"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { DEFAULT_ANALYTICS_SEARCH } from "@/lib/pagination"

const METRIC_LABELS: Record<string, string> = {
  ai_review_coverage: "AI Review Coverage",
  helpful_rate: "Helpful Rate",
  applied_or_fixed_findings_rate: "Applied or Fixed Findings",
}

function formatMetricValue(metricKey: string, value: number | null): string {
  if (value == null || !Number.isFinite(value)) {
    return "—"
  }
  if (
    metricKey === "helpful_rate" ||
    metricKey === "applied_or_fixed_findings_rate" ||
    metricKey === "ai_review_coverage"
  ) {
    return `${(value * 100).toFixed(1)}%`
  }
  return value.toFixed(2)
}

function formatWindow(start: string | null, end: string | null): string | null {
  if (!start || !end) return null
  return `${new Date(start).toLocaleDateString()} – ${new Date(end).toLocaleDateString()}`
}

function scopeDescription(analytics: DashboardAnalyticsSection): string {
  if (analytics.scope === "team" && analytics.team_name) {
    return `Team scope: ${analytics.team_name}`
  }
  if (analytics.scope === "team") {
    return "Team scope"
  }
  return "Organization scope"
}

export function DashboardAnalyticsHighlights({
  analytics,
  loading,
  error,
}: {
  analytics: DashboardAnalyticsSection | null | undefined
  loading?: boolean
  error?: boolean
}) {
  const windowLabel = analytics
    ? formatWindow(analytics.window_start, analytics.window_end)
    : null

  return (
    <Card className="border-border/70 shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-medium">Analytics highlights</CardTitle>
            <CardDescription>
              {analytics
                ? `${scopeDescription(analytics)}${windowLabel ? ` · ${windowLabel}` : ""}`
                : "Key review effectiveness metrics for your role"}
            </CardDescription>
          </div>
          <Link
            to="/analytics"
            search={
              analytics?.scope === "team" && analytics.team_id
                ? {
                    ...DEFAULT_ANALYTICS_SEARCH,
                    scope: "team",
                    team_id: analytics.team_id,
                  }
                : DEFAULT_ANALYTICS_SEARCH
            }
            className="text-muted-foreground hover:text-foreground shrink-0 text-xs font-medium"
          >
            View analytics
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <DataPanel loading={loading} error={error}>
          {!analytics || analytics.metrics.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              Analytics snapshot is not available yet. Data appears after reviews run
              and analytics are recomputed.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-3">
              {analytics.metrics.map((metric) => (
                <div
                  key={metric.metric_key}
                  className="rounded-lg border border-border/70 px-4 py-3"
                >
                  <p className="text-muted-foreground text-[11px] font-semibold tracking-[0.16em] uppercase">
                    {METRIC_LABELS[metric.metric_key] ?? metric.metric_key}
                  </p>
                  <p className="mt-2 text-2xl font-semibold tracking-tight">
                    {formatMetricValue(
                      metric.metric_key,
                      metric.metric_value_num,
                    )}
                  </p>
                  {metric.sample_size != null ? (
                    <p className="text-muted-foreground mt-1 text-xs">
                      Sample size {metric.sample_size}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </DataPanel>
      </CardContent>
    </Card>
  )
}
