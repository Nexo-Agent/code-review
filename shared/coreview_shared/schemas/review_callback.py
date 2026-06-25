"""Review callback event models (schema v1).

JSON Schema: ``review-callback-v1.schema.json`` in this directory.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReviewCallbackAgent(BaseModel):
    name: str
    version: str


class ReviewCallbackRequest(BaseModel):
    git_provider: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str = ""
    head_ref: str = ""
    base_ref: str = ""
    pr_title: str = ""
    pr_url: str = ""


class ReviewCallbackFinding(BaseModel):
    severity: str
    title: str
    body: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None


class ReviewCallbackGithubResult(BaseModel):
    summary_comment_posted: bool = False
    inline_comments_posted: int = 0
    inline_comments_skipped: int = 0


class ReviewCallbackResult(BaseModel):
    findings: list[ReviewCallbackFinding] = Field(default_factory=list)
    github: ReviewCallbackGithubResult = Field(
        default_factory=ReviewCallbackGithubResult
    )


class ReviewCallbackError(BaseModel):
    message: str
    code: str = "runtime_error"


ReviewCallbackEventType = Literal[
    "review.started",
    "review.completed",
    "review.failed",
]


class ReviewCallbackEvent(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    event: ReviewCallbackEventType
    review_id: str
    occurred_at: datetime
    agent: ReviewCallbackAgent
    request: ReviewCallbackRequest
    result: ReviewCallbackResult | None = None
    error: ReviewCallbackError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
