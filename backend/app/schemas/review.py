from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewFindingResponse(BaseModel):
    id: UUID
    severity: str
    file_path: str | None
    line_start: int | None
    line_end: int | None
    title: str
    body: str
    created_at: datetime


class ReviewResponse(BaseModel):
    id: UUID
    provider: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    status: str
    delivery_id: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    findings: list[ReviewFindingResponse] = Field(default_factory=list)


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
