from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.review import ReviewResponse


class DashboardReviewStatusCounts(BaseModel):
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0


class DashboardReviewsSection(BaseModel):
    total: int
    by_status: DashboardReviewStatusCounts
    recent: list[ReviewResponse] = Field(default_factory=list)


class DashboardResourcesSection(BaseModel):
    teams: int
    repositories: int
    users: int | None = None
    llm_providers: int | None = None


class DashboardOnboardingStep(BaseModel):
    key: str
    label: str
    done: bool


class DashboardOnboardingSection(BaseModel):
    steps: list[DashboardOnboardingStep] = Field(default_factory=list)
    all_complete: bool = False


class DashboardAnalyticsMetric(BaseModel):
    metric_key: str
    metric_value_num: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    sample_size: int | None = None


class DashboardAnalyticsSection(BaseModel):
    scope: str
    team_id: UUID | None = None
    team_name: str | None = None
    computed_at: datetime | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    metrics: list[DashboardAnalyticsMetric] = Field(default_factory=list)


class DashboardUsageSection(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int
    llm_call_count: int
    review_count: int
    window_start: datetime
    window_end: datetime


class DashboardCapabilities(BaseModel):
    reviews: bool = True
    resources: bool = True
    onboarding: bool = False
    analytics: bool = False
    usage: bool = False


class DashboardSummaryResponse(BaseModel):
    capabilities: DashboardCapabilities
    reviews: DashboardReviewsSection
    resources: DashboardResourcesSection
    onboarding: DashboardOnboardingSection
    analytics: DashboardAnalyticsSection | None = None
    usage: DashboardUsageSection | None = None
