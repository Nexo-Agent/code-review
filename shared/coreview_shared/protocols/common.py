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
class RemoteRepoAccess:
    """Provider-supplied inputs required by the shared local git workflow.

    The goal is to keep provider-specific repository access details as data.
    Shared workspace code can then prepare mirrors, worktrees, and local diffs
    without knowing whether the repository lives on GitHub, Azure DevOps,
    GitLab, or another platform.
    """

    clone_url: str
    auth_args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PreparedWorkspace:
    """Concrete local workspace artifacts produced by the git adapter.

    Providers use this data object to hand local checkout state back to the
    orchestration layer. Keeping the paths here avoids leaking mirror/worktree
    details into review runners or provider-specific publishing logic.
    """

    repo_base: Path
    mirror_path: Path
    worktree_path: Path
    workspace: Workspace


@dataclass(frozen=True, slots=True)
class PreparedReview:
    """Provider-agnostic review session assembled for one code review run.

    High-level review orchestration should prefer this object over calling
    provider-specific helpers directly. It bundles the normalized PR context,
    local workspace state, and optional provider-owned data needed later when
    publishing comments back to the remote platform.
    """

    context: PRContext
    workspace: PreparedWorkspace
    remote_access: RemoteRepoAccess
    provider_data: object | None = None


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    event_type: str
    action: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    delivery_id: str | None
    pr_title: str = ""
    pr_url: str = ""


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
