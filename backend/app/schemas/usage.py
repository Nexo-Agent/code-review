from datetime import datetime

from pydantic import BaseModel, Field


class UsageSummaryResponse(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int
    llm_call_count: int
    review_count: int
    window_start: datetime
    window_end: datetime


class UsageHistoryPointResponse(BaseModel):
    window_start: datetime
    window_end: datetime
    metric_value_num: float
    sample_size: int


class UsageHistoryResponse(BaseModel):
    metric_key: str
    window_start: datetime
    window_end: datetime
    points: list[UsageHistoryPointResponse] = Field(default_factory=list)


class UsageBreakdownItemResponse(BaseModel):
    dimension_id: str
    dimension_label: str
    review_count: int
    llm_call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    percent_of_total: float


class UsageBreakdownResponse(BaseModel):
    group_by: str
    window_start: datetime
    window_end: datetime
    items: list[UsageBreakdownItemResponse] = Field(default_factory=list)
