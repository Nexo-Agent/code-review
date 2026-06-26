from pathlib import Path
from typing import Protocol

from coreview_shared.protocols.common import (
    CommandRunner,
    InlineComment,
    InlineCommentsResult,
    PRContext,
    PreparedReview,
    PRMetadata,
    WebhookEvent,
    WorkspaceSpec,
)


class GitProvider(Protocol):
    """Remote git platform contract used by review orchestration.

    Design notes:
    - High-level review flows should call `prepare_review()` and
      `cleanup_review()` instead of stitching together provider-specific git
      steps themselves.
    - Providers are expected to be local-first: use shared local git workspace
      preparation whenever it can produce the same result as a remote API.
    - The older metadata/diff/comment methods remain available because the MCP
      tool surface still exposes them directly, but new provider integrations
      should treat `PreparedReview` as the primary abstraction for review runs.
    """

    def verify_webhook_signature(
        self, payload: bytes, signature: str | None, secret: str
    ) -> bool: ...

    async def prepare_review(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
        runner: CommandRunner,
    ) -> PreparedReview: ...

    async def cleanup_review(
        self,
        review: PreparedReview,
        runner: CommandRunner,
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
    ) -> None: ...

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
    ) -> None: ...

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
