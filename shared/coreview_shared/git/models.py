from dataclasses import dataclass
from typing import Literal

from coreview_shared.review import PRContext
from coreview_shared.workspace.models import PreparedWorkspace


@dataclass(frozen=True, slots=True)
class RemoteRepoAccess:
    """Provider-supplied inputs required by the shared local git workflow."""

    clone_url: str
    auth_args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PreparedReview:
    """Provider-agnostic review session assembled for one code review run."""

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
    finding_index: int | None = None


@dataclass(frozen=True, slots=True)
class ReviewCommentArtifact:
    comment_kind: Literal["summary", "inline"]
    remote_comment_id: str
    remote_thread_id: str | None = None
    body: str = ""
    path: str | None = None
    line: int | None = None
    side: str = "RIGHT"
    finding_index: int | None = None


@dataclass(frozen=True, slots=True)
class InlineCommentsResult:
    posted: tuple[ReviewCommentArtifact, ...]
    skipped: tuple[InlineComment, ...]
