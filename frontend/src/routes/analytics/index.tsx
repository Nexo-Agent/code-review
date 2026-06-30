import { createFileRoute } from "@tanstack/react-router"
import {
  Chart as ChartJS,
  type ChartConfiguration,
  type TooltipItem,
} from "chart.js/auto"
import {
  CalendarRange,
  Filter,
  GitBranch,
  RotateCcw,
} from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"

import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useMe } from "@/hooks/use-auth"
import {
  useRecomputeReviewAnalytics,
  useReviewAnalyticsHistory,
  useReviewAnalyticsScoped,
} from "@/hooks/use-review-analytics"
import { useOrgRepositoriesOptions, useTeams } from "@/hooks/use-teams"
import { isOrgAdmin } from "@/lib/permissions"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/analytics/")({
  validateSearch: (
    search: Record<string, unknown>,
  ): {
    scope: "all" | "team" | "repo"
    team_id: string
    repo_integration_id: string
  } => ({
    scope:
      search.scope === "team" || search.scope === "repo"
        ? search.scope
        : "all",
    team_id: typeof search.team_id === "string" ? search.team_id : "",
    repo_integration_id:
      typeof search.repo_integration_id === "string"
        ? search.repo_integration_id
        : "",
  }),
  component: AnalyticsPage,
})

const METRIC_LABELS: Record<string, string> = {
  pr_time_to_merge: "PR Time to Merge",
  review_ready_to_merge: "Review-Ready to Merge",
  time_to_first_human_reply: "Time to First Human Reply",
  helpful_rate: "Helpful Rate",
  applied_or_fixed_findings_rate: "Applied or Fixed Findings Rate",
  ai_review_coverage: "AI Review Coverage",
}

const METRIC_KEYS = Object.keys(METRIC_LABELS) as Array<keyof typeof METRIC_LABELS>

const HISTORY_RANGE_OPTIONS = [
  { value: "7d", label: "Last 7 days", days: 7 },
  { value: "30d", label: "Last 30 days", days: 30 },
  { value: "90d", label: "Last 90 days", days: 90 },
  { value: "custom", label: "Custom" },
] as const

const METRIC_COLORS: Record<keyof typeof METRIC_LABELS, string> = {
  ai_review_coverage: "#73BF69",
  helpful_rate: "#F2CC0C",
  applied_or_fixed_findings_rate: "#FF9830",
  pr_time_to_merge: "#5794F2",
  review_ready_to_merge: "#8F3BB8",
  time_to_first_human_reply: "#56D2B2",
}

type HistoryRangeOption = (typeof HISTORY_RANGE_OPTIONS)[number]["value"]

function resolveHistoryRangeDays(value: HistoryRangeOption): number {
  switch (value) {
    case "7d":
      return 7
    case "30d":
      return 30
    case "90d":
      return 90
    case "custom":
      return 30
  }
}

function formatWindow(start: string, end: string): string {
  return `${new Date(start).toLocaleDateString()} - ${new Date(end).toLocaleDateString()}`
}

function formatRelativeDate(value: string): string {
  return new Date(value).toLocaleString()
}

function formatDateInputValue(value: Date): string {
  return value.toISOString().slice(0, 10)
}

function formatTimelineTick(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  })
}

function scopeLabel(scope: "all" | "team" | "repo"): string {
  switch (scope) {
    case "all":
      return "All repositories"
    case "team":
      return "Team"
    case "repo":
      return "Repository"
  }
}

function formatMetricNumber(metricKey: string, value: number): string {
  if (!Number.isFinite(value)) {
    return "—"
  }
  switch (metricKey) {
    case "helpful_rate":
    case "applied_or_fixed_findings_rate":
    case "ai_review_coverage":
      return `${(value * 100).toFixed(1)}%`
    case "pr_time_to_merge":
    case "review_ready_to_merge":
    case "time_to_first_human_reply":
      return formatDuration(value)
    default:
      return value.toFixed(2)
  }
}

function formatDuration(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) {
    return "—"
  }
  const minutes = Math.round(totalSeconds / 60)
  if (minutes < 60) {
    return `${minutes}m`
  }
  const hours = Math.round(minutes / 60)
  if (hours < 24) {
    return `${hours}h`
  }
  const days = (hours / 24).toFixed(1)
  return `${days}d`
}

function buildChartColor(color: string): { line: string; fill: string; glow: string } {
  return {
    line: color,
    fill: `${color}22`,
    glow: `${color}55`,
  }
}

function TimelineChart({
  metricKey,
  points,
}: {
  metricKey: keyof typeof METRIC_LABELS
  points: Array<{
    computed_at: string
    metric_value_num: number
  }>
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  const chartConfig = useMemo<ChartConfiguration<"line">>(() => {
    const palette = buildChartColor(METRIC_COLORS[metricKey])

    return {
      type: "line",
      data: {
        labels: points.map((point) => formatTimelineTick(point.computed_at)),
        datasets: [
          {
            label: METRIC_LABELS[metricKey],
            data: points.map((point) => point.metric_value_num),
            borderColor: palette.line,
            backgroundColor: palette.fill,
            pointBackgroundColor: palette.line,
            pointBorderColor: "#111827",
            pointHoverBackgroundColor: palette.line,
            pointHoverBorderColor: "#E5E7EB",
            pointHoverRadius: 4,
            pointRadius: 0,
            borderWidth: 2,
            tension: 0.32,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: "index",
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            backgroundColor: "#111827",
            borderColor: "#374151",
            borderWidth: 1,
            titleColor: "#F9FAFB",
            bodyColor: "#E5E7EB",
            displayColors: false,
            callbacks: {
              label: (context: TooltipItem<"line">) =>
                formatMetricNumber(metricKey, Number(context.parsed.y ?? NaN)),
            },
          },
        },
        scales: {
          x: {
            grid: {
              color: "rgba(148, 163, 184, 0.12)",
              drawBorder: false,
            },
            ticks: {
              color: "#94A3B8",
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 6,
            },
          },
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(148, 163, 184, 0.12)",
              drawBorder: false,
            },
            ticks: {
              color: "#94A3B8",
              callback: (value) => formatMetricNumber(metricKey, Number(value)),
            },
          },
        },
      },
    }
  }, [metricKey, points])

  useEffect(() => {
    if (!canvasRef.current) {
      return
    }
    const chart = new ChartJS(canvasRef.current, chartConfig)
    return () => {
      chart.destroy()
    }
  }, [chartConfig])

  return <canvas ref={canvasRef} />
}

function AnalyticsTrendPanel({
  metricKey,
  historyRequest,
}: {
  metricKey: keyof typeof METRIC_LABELS
  historyRequest:
    | {
        metric_key: keyof typeof METRIC_LABELS
        scope: "all" | "team" | "repo"
        team_id?: string
        repo_integration_id?: string
        start: string
        end: string
      }
    | {
        metric_key: keyof typeof METRIC_LABELS
        scope: "all" | "team" | "repo"
        team_id?: string
        repo_integration_id?: string
        days: number
      }
}) {
  const history = useReviewAnalyticsHistory({
    ...historyRequest,
    metric_key: metricKey,
  })
  const historyPoints = history.data?.items ?? []
  const latestPoint = historyPoints[historyPoints.length - 1]
  const previousPoint = historyPoints[historyPoints.length - 2]
  const change =
    latestPoint && previousPoint
      ? latestPoint.metric_value_num - previousPoint.metric_value_num
      : null

  return (
    <Card className="overflow-hidden border border-border/70 bg-background shadow-sm">
      <CardContent className="p-0">
        <DataPanel
          loading={history.isPending}
          error={history.isError}
          errorMessage="Failed to load analytics history."
        >
          {historyPoints.length === 0 ? (
            <div className="flex min-h-72 flex-col items-center justify-center gap-2 px-6 py-10 text-center">
              <p className="text-sm font-medium">No timeline data yet</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Recompute analytics after review events arrive to build this trend.
              </p>
            </div>
          ) : (
            <div className="flex h-full flex-col">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/70 px-5 py-4">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <span
                      className="size-2.5 rounded-full"
                      style={{ backgroundColor: METRIC_COLORS[metricKey] }}
                    />
                    <p className="text-sm font-medium">{METRIC_LABELS[metricKey]}</p>
                  </div>
                  <div className="flex items-end gap-3">
                    <p className="text-3xl font-semibold tracking-tight">
                      {formatMetricNumber(
                        metricKey,
                        latestPoint?.metric_value_num ?? NaN,
                      )}
                    </p>
                    <p className="pb-1 text-xs text-muted-foreground">
                      {history.data
                        ? `${historyPoints.length} points`
                        : "Waiting for data"}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                    Delta
                  </p>
                  <p
                    className={cn(
                      "mt-2 text-sm font-medium",
                      change == null
                        ? "text-muted-foreground"
                        : change >= 0
                          ? "text-emerald-500"
                          : "text-rose-500",
                    )}
                  >
                    {change == null
                      ? "Not enough data"
                      : `${change >= 0 ? "+" : ""}${formatMetricNumber(
                          metricKey,
                          change,
                        )}`}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {latestPoint ? formatRelativeDate(latestPoint.computed_at) : "—"}
                  </p>
                </div>
              </div>

              <div className="h-72 px-4 py-4">
                <TimelineChart metricKey={metricKey} points={historyPoints} />
              </div>
            </div>
          )}
        </DataPanel>
      </CardContent>
    </Card>
  )
}

function AnalyticsPage() {
  const navigate = Route.useNavigate()
  const search = Route.useSearch()
  const me = useMe()
  const analytics = useReviewAnalyticsScoped(search)
  const recompute = useRecomputeReviewAnalytics()
  const teams = useTeams()
  const repositories = useOrgRepositoriesOptions()
  const canRecompute = isOrgAdmin(me.data)
  const [historyRange, setHistoryRange] = useState<HistoryRangeOption>("30d")
  const [customStart, setCustomStart] = useState(() =>
    formatDateInputValue(new Date(Date.now() - 29 * 24 * 60 * 60 * 1000)),
  )
  const [customEnd, setCustomEnd] = useState(() =>
    formatDateInputValue(new Date()),
  )

  const teamNameById = useMemo(() => {
    return new Map((teams.data?.items ?? []).map((team) => [team.id, team.name]))
  }, [teams.data?.items])

  const repoNameById = useMemo(() => {
    return new Map(
      (repositories.data?.items ?? []).map((repo) => [repo.id, repo.repo_full_name]),
    )
  }, [repositories.data?.items])

  const selectedTeamName =
    (search.team_id ? teamNameById.get(search.team_id) : undefined) ??
    "Selected team"
  const selectedRepoName =
    (search.repo_integration_id
      ? repoNameById.get(search.repo_integration_id)
      : undefined) ?? "Selected repository"

  const historyRequest = useMemo(() => {
    const common = {
      metric_key: "ai_review_coverage" as keyof typeof METRIC_LABELS,
      scope: search.scope,
      team_id: search.team_id || undefined,
      repo_integration_id: search.repo_integration_id || undefined,
    } as const

    if (historyRange === "custom") {
      return {
        ...common,
        start: `${customStart}T00:00:00.000Z`,
        end: `${customEnd}T23:59:59.999Z`,
      }
    }

    return {
      ...common,
      days: resolveHistoryRangeDays(historyRange),
    }
  }, [
    customEnd,
    customStart,
    historyRange,
    search.repo_integration_id,
    search.scope,
    search.team_id,
  ])

  async function handleRecompute() {
    try {
      const result = await recompute.mutateAsync({ window_days: 30 })
      toast.success(`Analytics recompute queued: ${result.task_id}`)
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to queue analytics recompute."
      toast.error(message)
    }
  }

  function updateScope(next: {
    scope: "all" | "team" | "repo"
    team_id?: string
    repo_integration_id?: string
  }) {
    void navigate({
      search: {
        scope: next.scope,
        team_id: next.team_id ?? "",
        repo_integration_id: next.repo_integration_id ?? "",
      },
      replace: true,
      resetScroll: false,
    })
  }

  function handleScopeChange(value: "all" | "team" | "repo") {
    if (value === "all") {
      updateScope({ scope: "all" })
      return
    }
    if (value === "team") {
      updateScope({
        scope: "team",
        team_id: search.team_id || teams.data?.items[0]?.id || "",
      })
      return
    }
    updateScope({
      scope: "repo",
      repo_integration_id:
        search.repo_integration_id || repositories.data?.items[0]?.id || "",
    })
  }

  return (
    <AppShell
      title="Analytics"
      description={
        analytics.data
          ? `Latest GitHub snapshot for ${formatWindow(
              analytics.data.window_start,
              analytics.data.window_end,
            )}`
          : "Workflow analytics aggregated from review engagement events."
      }
      actions={
        canRecompute ? (
          <Button
            type="button"
            variant="outline"
            className="border-border/70 bg-background hover:bg-muted/50"
            onClick={() => void handleRecompute()}
            disabled={recompute.isPending}
          >
            <RotateCcw className="mr-2 size-4" />
            {recompute.isPending ? "Queueing recompute" : "Recompute analytics"}
          </Button>
        ) : null
      }
    >
      <section className="rounded-[28px] border border-border/70 bg-background shadow-sm">
        <div className="p-5 sm:p-6">
          <div className="grid gap-4">
            <div className="grid gap-3 lg:grid-cols-[180px_minmax(240px,1fr)_180px] lg:items-end">
              <div className="min-w-0">
                <Label className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                  <Filter className="size-3.5" />
                  <span>Scope filter</span>
                </Label>
                <Select
                  value={search.scope}
                  onValueChange={(value: "all" | "team" | "repo") =>
                    handleScopeChange(value)
                  }
                >
                  <SelectTrigger className="h-10 border-border/70 bg-background shadow-none">
                    <SelectValue placeholder="Select scope" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{scopeLabel("all")}</SelectItem>
                    <SelectItem value="team">{scopeLabel("team")}</SelectItem>
                    <SelectItem value="repo">{scopeLabel("repo")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="min-w-0">
                <Label className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                  <GitBranch className="size-3.5" />
                  <span>Target</span>
                </Label>
                {search.scope === "team" ? (
                  <Select
                    value={search.team_id}
                    onValueChange={(value) =>
                      updateScope({ scope: "team", team_id: value })
                    }
                  >
                    <SelectTrigger className="h-10 border-border/70 bg-background shadow-none">
                      <SelectValue placeholder={selectedTeamName} />
                    </SelectTrigger>
                    <SelectContent>
                      {(teams.data?.items ?? []).map((team) => (
                        <SelectItem key={team.id} value={team.id}>
                          {team.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : search.scope === "repo" ? (
                  <Select
                    value={search.repo_integration_id}
                    onValueChange={(value) =>
                      updateScope({ scope: "repo", repo_integration_id: value })
                    }
                  >
                    <SelectTrigger className="h-10 border-border/70 bg-background shadow-none">
                      <SelectValue placeholder={selectedRepoName} />
                    </SelectTrigger>
                    <SelectContent>
                      {(repositories.data?.items ?? []).map((repo) => (
                        <SelectItem key={repo.id} value={repo.id}>
                          {repo.repo_full_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="flex h-10 items-center rounded-md border border-dashed border-border/70 bg-muted/20 px-3 text-sm text-muted-foreground">
                    All enabled repositories
                  </div>
                )}
              </div>

              <div className="min-w-0">
                <Label className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                  <CalendarRange className="size-3.5" />
                  <span>Time range</span>
                </Label>
                <Select
                  value={historyRange}
                  onValueChange={(value: HistoryRangeOption) => setHistoryRange(value)}
                >
                  <SelectTrigger className="h-10 border-border/70 bg-background shadow-none">
                    <SelectValue placeholder="Select range" />
                  </SelectTrigger>
                  <SelectContent>
                    {HISTORY_RANGE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {historyRange === "custom" ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:max-w-md">
                <div className="space-y-2">
                  <Label
                    htmlFor="analytics-range-start"
                    className="text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase"
                  >
                    Start date
                  </Label>
                  <Input
                    id="analytics-range-start"
                    type="date"
                    value={customStart}
                    onChange={(event) => setCustomStart(event.target.value)}
                    className="h-10 border-border/70 bg-background"
                  />
                </div>
                <div className="space-y-2">
                  <Label
                    htmlFor="analytics-range-end"
                    className="text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase"
                  >
                    End date
                  </Label>
                  <Input
                    id="analytics-range-end"
                    type="date"
                    value={customEnd}
                    onChange={(event) => setCustomEnd(event.target.value)}
                    className="h-10 border-border/70 bg-background"
                  />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="mt-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold tracking-tight">Line charts</h3>
            <p className="text-sm text-muted-foreground">
              Trendlines for every key review metric in the selected scope.
            </p>
          </div>
        </div>

        <div className="grid gap-4">
          {METRIC_KEYS.map((metricKey) => (
            <AnalyticsTrendPanel
              key={metricKey}
              metricKey={metricKey}
              historyRequest={historyRequest}
            />
          ))}
        </div>
      </section>
    </AppShell>
  )
}
