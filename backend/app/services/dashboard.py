from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg

from app.auth.dependencies import AuthContext
from app.rbac.catalog import ActionKey, RoleKey
from app.repositories.identity_providers import IdentityProviderRepository
from app.repositories.llm_providers import LlmProviderRepository
from app.repositories.organizations import DEFAULT_ORG_ID
from app.repositories.repo_integrations import RepoIntegrationRepository
from app.repositories.review_analytics import ReviewAnalyticsRepository
from app.repositories.reviews import ReviewRepository, ReviewRow
from app.repositories.teams import TeamRepository
from app.repositories.usage import UsageFilters, UsageRepository
from app.repositories.users import UserListFilters, UserRepository
from app.schemas.dashboard import (
    DashboardAnalyticsMetric,
    DashboardAnalyticsSection,
    DashboardCapabilities,
    DashboardOnboardingSection,
    DashboardOnboardingStep,
    DashboardResourcesSection,
    DashboardReviewsSection,
    DashboardReviewStatusCounts,
    DashboardSummaryResponse,
    DashboardUsageSection,
)
from app.schemas.review import ReviewResponse
from app.services.review_analytics_events import (
    analytics_provider_ids,
    supports_applied_fixed_metric,
)

DASHBOARD_METRIC_KEYS = (
    "ai_review_coverage",
    "helpful_rate",
    "applied_or_fixed_findings_rate",
)

RECENT_REVIEW_LIMIT = 5


def _has_org_action(auth: AuthContext, action: ActionKey) -> bool:
    if auth.user.is_org_admin or auth.user.is_superuser:
        return True
    if auth.permissions is None:
        return False
    return action.value in auth.permissions.organization_actions


def _has_team_action(auth: AuthContext, team_id: UUID, action: ActionKey) -> bool:
    if _has_org_action(auth, action):
        return True
    if auth.permissions is None:
        return False
    return action.value in auth.permissions.team_actions.get(str(team_id), [])


def _can_read_reviews(auth: AuthContext) -> bool:
    if _has_org_action(auth, ActionKey.REVIEW_READ):
        return True
    if auth.permissions is None:
        return bool(auth.accessible_team_ids)
    for team_id in auth.accessible_team_ids:
        if ActionKey.REVIEW_READ.value in auth.permissions.team_actions.get(
            str(team_id), []
        ):
            return True
    return False


def _is_org_admin(auth: AuthContext) -> bool:
    if auth.user.is_org_admin or auth.user.is_superuser:
        return True
    if auth.permissions is None:
        return False
    return RoleKey.ORG_ADMIN.value in auth.permissions.organization_roles


def _to_review_response(row: ReviewRow) -> ReviewResponse:
    return ReviewResponse(
        id=row.id,
        provider=row.provider,
        repo_full_name=row.repo_full_name,
        pr_number=row.pr_number,
        pr_title=row.pr_title,
        pr_url=row.pr_url,
        pr_author=row.pr_author,
        head_sha=row.head_sha,
        base_sha=row.base_sha,
        base_ref=row.base_ref,
        head_ref=row.head_ref,
        status=row.status,
        delivery_id=row.delivery_id,
        repo_integration_id=row.repo_integration_id,
        team_id=row.team_id,
        error_message=row.error_message,
        started_at=row.started_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        findings_count=row.findings_count,
        summary_comment_posted=row.summary_comment_posted,
        inline_comments_posted=row.inline_comments_posted,
        inline_comments_skipped=row.inline_comments_skipped,
    )


def _empty_summary() -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        capabilities=DashboardCapabilities(
            reviews=False,
            resources=False,
            onboarding=False,
            analytics=False,
            usage=False,
        ),
        reviews=DashboardReviewsSection(
            total=0,
            by_status=DashboardReviewStatusCounts(),
            recent=[],
        ),
        resources=DashboardResourcesSection(teams=0, repositories=0),
        onboarding=DashboardOnboardingSection(steps=[], all_complete=True),
    )


def _resolve_analytics_scope(
    auth: AuthContext,
) -> tuple[str, UUID | None]:
    if _is_org_admin(auth) or _has_org_action(auth, ActionKey.TEAM_CREATE):
        return "all", None
    if len(auth.accessible_team_ids) == 1:
        return "team", auth.accessible_team_ids[0]
    return "all", None


async def _build_analytics_section(
    conn: asyncpg.Connection,
    auth: AuthContext,
) -> DashboardAnalyticsSection | None:
    if not _can_read_reviews(auth):
        return None

    all_rows = await ReviewAnalyticsRepository(
        conn
    ).list_latest_metric_rows_for_providers(
        providers=list(analytics_provider_ids()),
    )
    if not all_rows:
        return None

    allowed_team_ids = set(auth.accessible_team_ids)
    rows = [
        row
        for row in all_rows
        if row.team_id is None or row.team_id in allowed_team_ids
    ]
    if not rows:
        return None

    scope, team_id = _resolve_analytics_scope(auth)
    team_name: str | None = None

    if scope == "team" and team_id is not None:
        team = await TeamRepository(conn).get(team_id)
        team_name = team.name if team else None
        scoped_rows = [
            row
            for row in rows
            if row.dimension_key == f"team:{team_id}" or row.team_id == team_id
        ]
    else:
        scoped_rows = [row for row in rows if row.dimension_key == "all"]
        if not scoped_rows:
            scoped_rows = rows

    latest = max(all_rows, key=lambda row: row.computed_at)
    metrics: list[DashboardAnalyticsMetric] = []
    for metric_key in DASHBOARD_METRIC_KEYS:
        if metric_key == "applied_or_fixed_findings_rate":
            candidates = [
                row
                for row in scoped_rows
                if row.metric_key == metric_key
                and supports_applied_fixed_metric(row.provider)
            ]
        else:
            candidates = [row for row in scoped_rows if row.metric_key == metric_key]
        if not candidates:
            continue
        match = candidates[0]
        metrics.append(
            DashboardAnalyticsMetric(
                metric_key=match.metric_key,
                metric_value_num=match.metric_value_num,
                numerator=match.numerator,
                denominator=match.denominator,
                sample_size=match.sample_size,
            )
        )

    if not metrics:
        return None

    return DashboardAnalyticsSection(
        scope=scope,
        team_id=team_id,
        team_name=team_name,
        computed_at=latest.computed_at,
        window_start=latest.window_start,
        window_end=latest.window_end,
        metrics=metrics,
    )


async def _build_onboarding_section(
    conn: asyncpg.Connection,
    auth: AuthContext,
    *,
    teams_count: int,
    repos_count: int,
    llm_count: int,
    reviews_total: int,
) -> DashboardOnboardingSection:
    steps: list[DashboardOnboardingStep] = []

    if _has_org_action(auth, ActionKey.TEAM_CREATE):
        steps.append(
            DashboardOnboardingStep(
                key="create_team",
                label="Create a team",
                done=teams_count > 0,
            )
        )

    can_connect_repo = _has_org_action(auth, ActionKey.REPO_CREATE) or any(
        _has_team_action(auth, team_id, ActionKey.REPO_CREATE)
        for team_id in auth.accessible_team_ids
    )
    if can_connect_repo:
        steps.append(
            DashboardOnboardingStep(
                key="connect_repo",
                label="Connect a repository",
                done=repos_count > 0,
            )
        )

    if _has_org_action(auth, ActionKey.SETTINGS_LLM_READ):
        steps.append(
            DashboardOnboardingStep(
                key="configure_llm",
                label="Configure an LLM provider",
                done=llm_count > 0,
            )
        )

    if _can_read_reviews(auth):
        steps.append(
            DashboardOnboardingStep(
                key="first_review",
                label="Run your first review",
                done=reviews_total > 0,
            )
        )

    if _has_org_action(auth, ActionKey.SETTINGS_SSO_READ):
        idp = await IdentityProviderRepository(conn).get(DEFAULT_ORG_ID)
        steps.append(
            DashboardOnboardingStep(
                key="configure_sso",
                label="Configure SSO",
                done=bool(idp and idp.enabled),
            )
        )

    all_complete = bool(steps) and all(step.done for step in steps)
    return DashboardOnboardingSection(steps=steps, all_complete=all_complete)


async def get_dashboard_summary(
    conn: asyncpg.Connection,
    auth: AuthContext,
) -> DashboardSummaryResponse:
    team_ids = auth.accessible_team_ids
    if not team_ids:
        return _empty_summary()

    review_repo = ReviewRepository(conn)
    status_counts = await review_repo.count_reviews_by_status(team_ids=team_ids)
    total_reviews = sum(status_counts.values())
    recent_rows = await review_repo.list_reviews(
        team_ids=team_ids,
        limit=RECENT_REVIEW_LIMIT,
        offset=0,
    )

    teams_count = await TeamRepository(conn).count_for_teams(team_ids=team_ids)
    repos_count = await RepoIntegrationRepository(conn).count_for_teams(
        team_ids=team_ids
    )

    users_count: int | None = None
    if _has_org_action(auth, ActionKey.USER_READ):
        users_count = await UserRepository(conn).count(filters=UserListFilters())

    llm_count = 0
    llm_providers_count: int | None = None
    if _has_org_action(auth, ActionKey.SETTINGS_LLM_READ):
        llm_count = await LlmProviderRepository(conn).count(
            organization_id=DEFAULT_ORG_ID
        )
        llm_providers_count = llm_count

    onboarding = await _build_onboarding_section(
        conn,
        auth,
        teams_count=teams_count,
        repos_count=repos_count,
        llm_count=llm_count,
        reviews_total=total_reviews,
    )

    show_onboarding = bool(onboarding.steps) and not onboarding.all_complete

    analytics: DashboardAnalyticsSection | None = None
    if _can_read_reviews(auth):
        analytics = await _build_analytics_section(conn, auth)

    usage: DashboardUsageSection | None = None
    if _has_org_action(auth, ActionKey.SETTINGS_USAGE_READ):
        window_end = datetime.now(tz=UTC)
        window_start = window_end - timedelta(days=30)
        usage_filters = UsageFilters(start=window_start, end=window_end)
        summary = await UsageRepository(conn).query_summary(usage_filters)
        usage = DashboardUsageSection(
            total_tokens=summary.total_tokens,
            input_tokens=summary.input_tokens,
            output_tokens=summary.output_tokens,
            llm_call_count=summary.llm_call_count,
            review_count=summary.review_count,
            window_start=window_start,
            window_end=window_end,
        )

    return DashboardSummaryResponse(
        capabilities=DashboardCapabilities(
            reviews=_can_read_reviews(auth),
            resources=True,
            onboarding=show_onboarding,
            analytics=analytics is not None,
            usage=usage is not None,
        ),
        reviews=DashboardReviewsSection(
            total=total_reviews,
            by_status=DashboardReviewStatusCounts(**status_counts),
            recent=[_to_review_response(row) for row in recent_rows],
        ),
        resources=DashboardResourcesSection(
            teams=teams_count,
            repositories=repos_count,
            users=users_count,
            llm_providers=llm_providers_count,
        ),
        onboarding=onboarding,
        analytics=analytics,
        usage=usage,
    )
