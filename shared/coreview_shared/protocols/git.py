from pathlib import Path
from typing import Protocol

from coreview_shared.protocols.common import (
    CommandRunner,
    InlineComment,
    InlineCommentsResult,
    PRContext,
    PRMetadata,
    WebhookEvent,
    WorkspaceSpec,
)


class GitProvider(Protocol):
    def verify_webhook_signature(
        self, payload: bytes, signature: str | None, secret: str
    ) -> bool: ...

    async def get_pr_metadata(
        self, repo_full_name: str, pr_number: int
    ) -> PRMetadata: ...

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str: ...

    async def fetch_pr_context(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> PRContext: ...

    async def ensure_worktree(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
        runner: CommandRunner,
    ) -> Path: ...

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
