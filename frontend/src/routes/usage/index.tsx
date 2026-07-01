import { createFileRoute } from "@tanstack/react-router"
import {
  Chart as ChartJS,
  type ChartConfiguration,
  type TooltipItem,
} from "chart.js/auto"
import { CalendarRange, Filter } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"

import type { UsageMetricKey } from "@/api/usage-types"
import { AppShell } from "@/components/layout/AppShell"
import { DataPanel } from "@/components/patterns/data-panel"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useLlmProviders } from "@/hooks/use-settings"
import { useTeams } from "@/hooks/use-teams"
import {
  useUsageBreakdown,
  useUsageHistory,
  useUsageSummary,
} from "@/hooks/use-usage"
import { requireOrgPermission } from "@/lib/permissions"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/usage/")({
  beforeLoad: requireOrgPermission("settings.usage.read"),
  validateSearch: (
    search: Record<string, unknown>,
  ): {
    team_id: string
    repo_integration_id: string
    git_provider: string
    llm_provider_id: string
  } => ({
    team_id: typeof search.team_id === "string" ? search.team_id : "",
    repo_integration_id:
      typeof search.repo_integration_id === "string"
        ? search.repo_integration_id
        : "",
    git_provider: typeof search.git_provider === "string" ? search.git_provider : "",
    llm_provider_id:
      typeof search.llm_provider_id === "string" ? search.llm_provider_id : "",
  }),
  component: UsagePage,
})

const HISTORY_RANGE_OPTIONS = [
  { value: "7d", label: "Last 7 days", days: 7 },
  { value: "30d", label: "Last 30 days", days: 30 },
  { value: "90d", label: "Last 90 days", days: 90 },
  { value: "custom", label: "Custom" },
] as const

const GIT_PROVIDER_OPTIONS = [
  { value: "all", label: "All git providers" },
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
  { value: "azure-devops", label: "Azure DevOps" },
  { value: "bitbucket", label: "Bitbucket" },
  { value: "bitbucket-dc", label: "Bitbucket Data Center" },
] as const

const METRIC_OPTIONS: Array<{ value: UsageMetricKey; label: string }> = [
  { value: "total_tokens", label: "Total tokens" },
  { value: "input_tokens", label: "Input tokens" },
  { value: "output_tokens", label: "Output tokens" },
  { value: "llm_call_count", label: "LLM calls" },
]

const BREAKDOWN_TABS = [
  { value: "team", label: "Team" },
  { value: "repo", label: "Repository" },
  { value: "llm_provider", label: "LLM Provider" },
] as const

type HistoryRangeOption = (typeof HISTORY_RANGE_OPTIONS)[number]["value"]
type BreakdownTab = (typeof BREAKDOWN_TABS)[number]["value"]

const CHART_COLORS: Record<UsageMetricKey, string> = {
  total_tokens: "#5794F2",
  input_tokens: "#8F3BB8",
  output_tokens: "#56D2B2",
  llm_call_count: "#F2CC0C",
  review_count: "#73BF69",
}

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

function formatDateInputValue(value: Date): string {
  return value.toISOString().slice(0, 10)
}

function formatWindow(start: string, end: string): string {
  return `${new Date(start).toLocaleDateString()} - ${new Date(end).toLocaleDateString()}`
}

function formatTokenCount(value: number): string {
  if (!Number.isFinite(value)) {
    return "—"
  }
  return new Intl.NumberFormat().format(Math.round(value))
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) {
    return "—"
  }
  return `${value.toFixed(1)}%`
}

function formatTimelineTick(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  })
}

function UsageTimelineChart({
  metric,
  points,
}: {
  metric: UsageMetricKey
  points: Array<{ window_start: string; metric_value_num: number }>
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const color = CHART_COLORS[metric]

  const chartConfig = useMemo<ChartConfiguration<"line">>(() => {
    return {
      type: "line",
      data: {
        labels: points.map((point) => formatTimelineTick(point.window_start)),
        datasets: [
          {
            label: metric,
            data: points.map((point) => point.metric_value_num),
            borderColor: color,
            backgroundColor: `${color}22`,
            pointBackgroundColor: color,
            pointBorderColor: "#111827",
            pointHoverBackgroundColor: color,
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
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#111827",
            borderColor: "#374151",
            borderWidth: 1,
            titleColor: "#F9FAFB",
            bodyColor: "#E5E7EB",
            displayColors: false,
            callbacks: {
              label: (context: TooltipItem<"line">) =>
                formatTokenCount(Number(context.parsed.y ?? NaN)),
            },
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(148, 163, 184, 0.12)", drawBorder: false },
            ticks: { color: "#94A3B8", maxRotation: 0, autoSkip: true, maxTicksLimit: 6 },
          },
          y: {
            beginAtZero: true,
            grid: { color: "rgba(148, 163, 184, 0.12)", drawBorder: false },
            ticks: {
              color: "#94A3B8",
              callback: (value) => formatTokenCount(Number(value)),
            },
          },
        },
      },
    }
  }, [color, metric, points])

  useEffect(() => {
    if (!canvasRef.current) {
      return
    }
    const chart = new ChartJS(canvasRef.current, chartConfig)
    return () => chart.destroy()
  }, [chartConfig])

  return <canvas ref={canvasRef} className="h-full w-full" />
}

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <Card className="border-border/70 bg-background shadow-sm">
      <CardContent className="p-5">
        <p className="text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
          {label}
        </p>
        <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
        {hint ? <p className="mt-1 text-sm text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  )
}

function UsagePage() {
  const navigate = Route.useNavigate()
  const search = Route.useSearch()
  const teams = useTeams()
  const llmProviders = useLlmProviders()
  const [historyRange, setHistoryRange] = useState<HistoryRangeOption>("30d")
  const [chartMetric, setChartMetric] = useState<UsageMetricKey>("total_tokens")
  const [breakdownTab, setBreakdownTab] = useState<BreakdownTab>("team")
  const [customStart, setCustomStart] = useState(() =>
    formatDateInputValue(new Date(Date.now() - 29 * 24 * 60 * 60 * 1000)),
  )
  const [customEnd, setCustomEnd] = useState(() => formatDateInputValue(new Date()))

  const usageFilters = useMemo(() => {
    const common = {
      team_id: search.team_id || undefined,
      repo_integration_id: search.repo_integration_id || undefined,
      git_provider:
        search.git_provider && search.git_provider !== "all"
          ? search.git_provider
          : undefined,
      llm_provider_id: search.llm_provider_id || undefined,
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
    search.git_provider,
    search.llm_provider_id,
    search.repo_integration_id,
    search.team_id,
  ])

  const summary = useUsageSummary(usageFilters)
  const history = useUsageHistory({ ...usageFilters, metric: chartMetric })
  const breakdown = useUsageBreakdown({
    ...usageFilters,
    group_by: breakdownTab,
  })

  function updateSearch(next: Partial<typeof search>) {
    void navigate({
      search: { ...search, ...next },
      replace: true,
      resetScroll: false,
    })
  }

  return (
    <AppShell
      title="Usage"
      description={
        summary.data
          ? `Token usage for ${formatWindow(
              summary.data.window_start,
              summary.data.window_end,
            )}`
          : "Organization-wide LLM token usage across reviews."
      }
    >
      <section className="rounded-[28px] border border-border/70 bg-background shadow-sm">
        <div className="p-5 sm:p-6">
          <div className="grid gap-4">
            <div className="grid gap-3 xl:grid-cols-4 lg:grid-cols-2">
              <div className="min-w-0">
                <Label className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                  <Filter className="size-3.5" />
                  <span>Team</span>
                </Label>
                <Select
                  value={search.team_id || "all"}
                  onValueChange={(value) =>
                    updateSearch({ team_id: value === "all" ? "" : value })
                  }
                >
                  <SelectTrigger className="h-10 border-border/70 bg-background shadow-none">
                    <SelectValue placeholder="All teams" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All teams</SelectItem>
                    {(teams.data?.items ?? []).map((team) => (
                      <SelectItem key={team.id} value={team.id}>
                        {team.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="min-w-0">
                <Label className="mb-2 block text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                  Git provider
                </Label>
                <Select
                  value={search.git_provider || "all"}
                  onValueChange={(value) => updateSearch({ git_provider: value })}
                >
                  <SelectTrigger className="h-10 border-border/70 bg-background shadow-none">
                    <SelectValue placeholder="All git providers" />
                  </SelectTrigger>
                  <SelectContent>
                    {GIT_PROVIDER_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="min-w-0">
                <Label className="mb-2 block text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                  LLM provider
                </Label>
                <Select
                  value={search.llm_provider_id || "all"}
                  onValueChange={(value) =>
                    updateSearch({ llm_provider_id: value === "all" ? "" : value })
                  }
                >
                  <SelectTrigger className="h-10 border-border/70 bg-background shadow-none">
                    <SelectValue placeholder="All LLM providers" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All LLM providers</SelectItem>
                    {(llmProviders.data?.items ?? []).map((provider) => (
                      <SelectItem key={provider.id} value={provider.id}>
                        {provider.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
                  <Label htmlFor="usage-range-start">Start</Label>
                  <Input
                    id="usage-range-start"
                    type="date"
                    value={customStart}
                    onChange={(event) => setCustomStart(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="usage-range-end">End</Label>
                  <Input
                    id="usage-range-end"
                    type="date"
                    value={customEnd}
                    onChange={(event) => setCustomEnd(event.target.value)}
                  />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="Total tokens"
          value={formatTokenCount(summary.data?.total_tokens ?? 0)}
          hint={
            summary.data
              ? `${formatTokenCount(summary.data.review_count)} reviews`
              : undefined
          }
        />
        <SummaryCard
          label="Input tokens"
          value={formatTokenCount(summary.data?.input_tokens ?? 0)}
        />
        <SummaryCard
          label="Output tokens"
          value={formatTokenCount(summary.data?.output_tokens ?? 0)}
        />
        <SummaryCard
          label="LLM calls"
          value={formatTokenCount(summary.data?.llm_call_count ?? 0)}
        />
      </div>

      <div className="mt-6">
        <Card className="overflow-hidden border border-border/70 bg-background shadow-sm">
          <CardContent className="p-0">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/70 px-5 py-4">
              <div>
                <p className="text-sm font-medium">Usage trend</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Daily token usage across the selected filters.
                </p>
              </div>
              <Select
                value={chartMetric}
                onValueChange={(value: UsageMetricKey) => setChartMetric(value)}
              >
                <SelectTrigger className="h-9 w-[180px] border-border/70 bg-background shadow-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {METRIC_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DataPanel
              loading={history.isPending}
              error={history.isError}
              errorMessage="Failed to load usage history."
            >
              <div className="h-[280px] p-5">
                {history.data?.points.length ? (
                  <UsageTimelineChart metric={chartMetric} points={history.data.points} />
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    No usage data for the selected window.
                  </div>
                )}
              </div>
            </DataPanel>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <Card className="overflow-hidden border border-border/70 bg-background shadow-sm">
          <CardContent className="p-5">
            <div className="mb-4">
              <p className="text-sm font-medium">Breakdown</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Token usage grouped by team, repository, or LLM provider.
              </p>
            </div>
          <div className="mb-4 flex flex-wrap gap-2">
            {BREAKDOWN_TABS.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setBreakdownTab(tab.value)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-sm transition-colors",
                  breakdownTab === tab.value
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border/70 bg-background text-muted-foreground hover:bg-muted/50",
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="text-right">Reviews</TableHead>
                <TableHead className="text-right">LLM calls</TableHead>
                <TableHead className="text-right">Input</TableHead>
                <TableHead className="text-right">Output</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Share</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(breakdown.data?.items ?? []).map((item) => (
                <TableRow key={`${breakdownTab}-${item.dimension_id}`}>
                  <TableCell className="font-medium">{item.dimension_label}</TableCell>
                  <TableCell className="text-right">
                    {formatTokenCount(item.review_count)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatTokenCount(item.llm_call_count)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatTokenCount(item.input_tokens)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatTokenCount(item.output_tokens)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatTokenCount(item.total_tokens)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatPercent(item.percent_of_total)}
                  </TableCell>
                </TableRow>
              ))}
              {!breakdown.data?.items.length ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                    No usage data for the selected window.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
