from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PRMetadata:
    repo_full_name: str
    pr_number: int
    title: str
    author: str
    head_sha: str
    base_sha: str
    head_ref: str
    base_ref: str
    html_url: str


@dataclass(frozen=True, slots=True)
class PRContext:
    metadata: PRMetadata
    diff: str
    ci_summary: str = ""


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    severity: str
    title: str
    body: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceSpec:
    review_id: str
    repo_full_name: str
    pr_number: int
    head_sha: str


@dataclass(frozen=True, slots=True)
class Workspace:
    path: Path
    spec: WorkspaceSpec


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    event_type: str
    action: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    delivery_id: str | None
    pr_title: str = ""


@dataclass(frozen=True, slots=True)
class InlineComment:
    path: str
    line: int
    body: str
    side: str = "RIGHT"


@dataclass(frozen=True, slots=True)
class InlineCommentsResult:
    posted: tuple[InlineComment, ...]
    skipped: tuple[InlineComment, ...]


class CommandRunner(Protocol):
    async def run(self, args: list[str], cwd: Path) -> None: ...
