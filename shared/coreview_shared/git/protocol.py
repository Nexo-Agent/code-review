from pathlib import Path
from typing import Protocol

from coreview_shared.git.models import (
    InlineComment,
    InlineCommentsResult,
    PreparedReview,
    ReviewCommentArtifact,
    WebhookEvent,
)
from coreview_shared.review import PRContext, PRMetadata
from coreview_shared.workspace.models import WorkspaceSpec


class GitProvider(Protocol):
    """Remote git platform contract used by review orchestration."""

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str | None,
        secret: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bool: ...

    async def prepare_review(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
    ) -> PreparedReview: ...

    async def cleanup_review(
        self,
        review: PreparedReview,
    ) -> None: ...

    async def get_pr_metadata(
        self, repo_full_name: str, pr_number: int
    ) -> PRMetadata: ...

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str: ...

    async def fetch_pr_context(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> PRContext: ...

    async def publish_summary_comment(
        self,
        review: PreparedReview,
        body: str,
    ) -> ReviewCommentArtifact | None: ...

    async def publish_inline_comments(
        self,
        review: PreparedReview,
        comments: list[InlineComment],
        body: str = "",
    ) -> InlineCommentsResult: ...

    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> ReviewCommentArtifact | None: ...

    async def post_inline_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        comments: list[InlineComment],
        body: str = "",
        diff: str | None = None,
    ) -> InlineCommentsResult: ...

    def parse_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookEvent | None: ...

    def build_pr_url(self, repo_full_name: str, pr_number: int) -> str: ...

    def build_blob_url(
        self,
        repo_full_name: str,
        ref: str,
        file_path: str,
        line: int | None = None,
    ) -> str | None: ...
