import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { AppShell } from "@/components/layout/AppShell"
import { DashboardAnalyticsHighlights } from "@/components/dashboard/DashboardAnalyticsHighlights"
import { DashboardOnboardingChecklist } from "@/components/dashboard/DashboardOnboardingChecklist"
import { DashboardResourceOverview } from "@/components/dashboard/DashboardResourceOverview"
import { DashboardReviewActivity } from "@/components/dashboard/DashboardReviewActivity"
import { DashboardUsageSummary } from "@/components/dashboard/DashboardUsageSummary"
import { CodeHint, InlineError } from "@/components/patterns/inline-error"
import { useMe } from "@/hooks/use-auth"
import { useDashboard } from "@/hooks/use-dashboard"
import {
  dismissOnboarding,
  isOnboardingDismissed,
} from "@/lib/dashboard-onboarding"

export const Route = createFileRoute("/")({
  component: DashboardPage,
})

function DashboardPage() {
  const me = useMe()
  const dashboard = useDashboard()
  const [dismissedThisSession, setDismissedThisSession] = useState(false)

  const userId = me.data?.user.id
  const userName = me.data?.user.name || me.data?.user.email || "there"
  const summary = dashboard.data
  const loading = dashboard.isPending
  const error = dashboard.isError
  const onboardingDismissed =
    dismissedThisSession || Boolean(userId && isOnboardingDismissed(userId))

  const showOnboarding =
    summary?.capabilities.onboarding === true &&
    !onboardingDismissed &&
    (summary.onboarding.steps.length ?? 0) > 0

  function handleDismissOnboarding() {
    if (!userId) return
    dismissOnboarding(userId)
    setDismissedThisSession(true)
  }

  return (
    <AppShell
      title="Dashboard"
      description={`Welcome back, ${userName}`}
    >
      {error ? (
        <InlineError
          message="Failed to load dashboard. Start backend with"
          hint={<CodeHint>make dev</CodeHint>}
        />
      ) : (
        <div className="grid gap-4">
          {showOnboarding ? (
            <DashboardOnboardingChecklist
              steps={summary.onboarding.steps}
              onDismiss={handleDismissOnboarding}
            />
          ) : null}

          {summary?.capabilities.reviews !== false ? (
            <DashboardReviewActivity
              reviews={summary?.reviews}
              loading={loading}
              error={error}
            />
          ) : null}

          {summary?.capabilities.analytics ? (
            <DashboardAnalyticsHighlights
              analytics={summary?.analytics}
              loading={loading}
              error={error}
            />
          ) : null}

          <div className="grid gap-3 lg:grid-cols-2 lg:items-stretch">
            {summary?.capabilities.resources !== false ? (
              <DashboardResourceOverview
                resources={summary?.resources}
                loading={loading}
                error={error}
              />
            ) : null}

            {summary?.capabilities.usage ? (
              <DashboardUsageSummary
                usage={summary?.usage}
                loading={loading}
                error={error}
              />
            ) : null}
          </div>
        </div>
      )}
    </AppShell>
  )
}
