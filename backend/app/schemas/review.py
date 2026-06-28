from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse


class ReviewFindingResponse(BaseModel):
    id: UUID
    severity: str
    file_path: str | None
    line_start: int | None
    line_end: int | None
    title: str
    body: str
    code_url: str | None = None
    created_at: datetime


class ReviewResponse(BaseModel):
    id: UUID
    provider: str
    repo_full_name: str
    pr_number: int
    pr_title: str = ""
    pr_url: str = ""
    pr_author: str = ""
    head_sha: str
    base_sha: str = ""
    base_ref: str = ""
    head_ref: str = ""
    status: str
    delivery_id: str | None
    repo_integration_id: UUID | None = None
    team_id: UUID
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    findings_count: int = 0
    summary_comment_posted: bool = False
    inline_comments_posted: int = 0
    inline_comments_skipped: int = 0
    findings: list[ReviewFindingResponse] = Field(default_factory=list)


class ReviewListResponse(PaginatedResponse[ReviewResponse]):
    pass
