from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewAnalyticsRecomputeRequest(BaseModel):
    window_days: int = Field(default=30, ge=1, le=365)
    window_end: datetime | None = None


class ReviewAnalyticsRecomputeResponse(BaseModel):
    task_id: str
    window_days: int
    window_end: datetime | None = None


class ReviewAnalyticsJobResult(BaseModel):
    job_run_id: UUID
    window_start: datetime
    window_end: datetime
    rows_upserted: int


class ReviewAnalyticsMetricResponse(BaseModel):
    metric_key: str
    provider: str
    granularity: str
    window_start: datetime
    window_end: datetime
    dimension_key: str
    repo_integration_id: UUID | None = None
    team_id: UUID | None = None
    repo_full_name: str = ""
    metric_value_num: float
    numerator: float | None = None
    denominator: float | None = None
    sample_size: int
    dimensions_json: dict = Field(default_factory=dict)
    job_run_id: UUID
    computed_at: datetime


class ReviewAnalyticsSnapshotResponse(BaseModel):
    job_run_id: UUID
    computed_at: datetime
    window_start: datetime
    window_end: datetime
    items: list[ReviewAnalyticsMetricResponse] = Field(default_factory=list)


class ReviewAnalyticsHistoryPointResponse(BaseModel):
    metric_key: str
    provider: str
    dimension_key: str
    repo_integration_id: UUID | None = None
    team_id: UUID | None = None
    repo_full_name: str = ""
    metric_value_num: float
    numerator: float | None = None
    denominator: float | None = None
    sample_size: int
    computed_at: datetime
    window_start: datetime
    window_end: datetime


class ReviewAnalyticsHistoryResponse(BaseModel):
    metric_key: str
    scope: str
    team_id: UUID | None = None
    repo_integration_id: UUID | None = None
    range_start: datetime
    range_end: datetime
    items: list[ReviewAnalyticsHistoryPointResponse] = Field(default_factory=list)
