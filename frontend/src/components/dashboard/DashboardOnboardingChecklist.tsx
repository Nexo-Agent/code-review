import type { DashboardOnboardingStep } from "@/api/dashboard-types"
import { Button } from "@/components/ui/button"
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
  DEFAULT_REVIEWS_SEARCH,
} from "@/lib/pagination"
import { Link } from "@tanstack/react-router"
import { CheckCircle2, Circle, X } from "lucide-react"

const STEP_ROUTES: Record<
  string,
  { to: string; search?: Record<string, unknown> }
> = {
  create_team: { to: "/teams", search: DEFAULT_LIST_SEARCH },
  connect_repo: {
    to: "/repositories",
    search: DEFAULT_REPOSITORIES_SEARCH,
  },
  configure_llm: { to: "/llm-providers", search: DEFAULT_LIST_SEARCH },
  first_review: { to: "/reviews", search: DEFAULT_REVIEWS_SEARCH },
  configure_sso: { to: "/settings/identity-provider" },
}

export function DashboardOnboardingChecklist({
  steps,
  onDismiss,
}: {
  steps: DashboardOnboardingStep[]
  onDismiss: () => void
}) {
  const incomplete = steps.filter((step) => !step.done)

  return (
    <Card className="border-border/70 shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-medium">Getting started</CardTitle>
            <CardDescription>
              {incomplete.length > 0
                ? `${incomplete.length} step${incomplete.length === 1 ? "" : "s"} remaining`
                : "All setup steps are complete"}
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="text-muted-foreground size-8 shrink-0"
            onClick={onDismiss}
            aria-label="Dismiss getting started checklist"
          >
            <X className="size-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <ul className="grid gap-2">
          {steps.map((step) => {
            const route = STEP_ROUTES[step.key]
            const Icon = step.done ? CheckCircle2 : Circle
            const content = (
              <span className="flex items-center gap-2.5 text-sm">
                <Icon
                  className={
                    step.done
                      ? "size-4 shrink-0 text-emerald-500"
                      : "text-muted-foreground size-4 shrink-0"
                  }
                />
                <span className={step.done ? "text-muted-foreground line-through" : ""}>
                  {step.label}
                </span>
              </span>
            )

            if (step.done || !route) {
              return (
                <li key={step.key} className="rounded-md px-1 py-0.5">
                  {content}
                </li>
              )
            }

            return (
              <li key={step.key}>
                <Link
                  to={route.to}
                  search={route.search}
                  className="hover:bg-muted/50 block rounded-md px-1 py-0.5 transition-colors"
                >
                  {content}
                </Link>
              </li>
            )
          })}
        </ul>
      </CardContent>
    </Card>
  )
}
