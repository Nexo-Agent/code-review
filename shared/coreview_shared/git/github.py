import hashlib
import hmac
import json
import logging
from pathlib import Path

import httpx

from coreview_shared.git.diff_lines import filter_inline_comments
from coreview_shared.git.models import (
    InlineComment,
    InlineCommentsResult,
    PreparedReview,
    RemoteRepoAccess,
    ReviewCommentArtifact,
    WebhookEvent,
)
from coreview_shared.review import PRContext, PRMetadata
from coreview_shared.workspace.git_workspace import GitWorkspace
from coreview_shared.workspace.models import WorkspaceSpec

logger = logging.getLogger(__name__)

HANDLED_WEBHOOK_ACTIONS = frozenset({"opened", "synchronize", "reopened"})


class GitHubProvider:
    API_BASE = "https://api.github.com"

    def __init__(
        self,
        token: str,
        *,
        git_workspace: GitWorkspace | None = None,
    ) -> None:
        self._token = token
        self._git_workspace = git_workspace or GitWorkspace()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _clone_url(self, repo_full_name: str) -> str:
        return f"https://x-access-token:{self._token}@github.com/{repo_full_name}.git"

    def _remote_access(self, repo_full_name: str) -> RemoteRepoAccess:
        return RemoteRepoAccess(clone_url=self._clone_url(repo_full_name))

    def build_pr_url(self, repo_full_name: str, pr_number: int) -> str:
        return f"https://github.com/{repo_full_name}/pull/{pr_number}"

    def build_blob_url(
        self,
        repo_full_name: str,
        ref: str,
        file_path: str,
        line: int | None = None,
    ) -> str | None:
        if not file_path.strip():
            return None
        base = f"https://github.com/{repo_full_name}/blob/{ref}/{file_path}"
        return f"{base}#L{line}" if line else base

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str | None,
        secret: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bool:
        del headers
        if not secret:
            return False
        if not signature or not signature.startswith("sha256="):
            return False
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature.removeprefix("sha256="), expected)

    def parse_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookEvent | None:
        normalized = {k.lower(): v for k, v in headers.items()}
        event_type = normalized.get("x-github-event", "")
        if event_type != "pull_request":
            return None

        payload = json.loads(body)
        action = payload.get("action", "")
        if action not in HANDLED_WEBHOOK_ACTIONS:
            return None

        pr = payload.get("pull_request")
        repo = payload.get("repository")
        if not pr or not repo:
            return None

        pr_url = pr.get("html_url") or self.build_pr_url(
            repo["full_name"], pr["number"]
        )

        return WebhookEvent(
            event_type=event_type,
            action=action,
            repo_full_name=repo["full_name"],
            pr_number=pr["number"],
            head_sha=pr["head"]["sha"],
            delivery_id=normalized.get("x-github-delivery"),
            pr_title=pr.get("title") or "",
            pr_url=pr_url,
        )

    async def prepare_review(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
    ) -> PreparedReview:
        """Prepare a provider-agnostic review session using local git artifacts.

        GitHub exposes a diff API, but review execution should still prefer the
        shared local git workflow so every provider converges on the same local
        behavior once a worktree exists.
        """

        metadata = await self.get_pr_metadata(spec.repo_full_name, spec.pr_number)
        if spec.head_sha and metadata.head_sha != spec.head_sha:
            logger.warning(
                "PR head SHA mismatch: expected %s, API returned %s",
                spec.head_sha[:7],
                metadata.head_sha[:7],
            )

        access = self._remote_access(spec.repo_full_name)
        prepared_workspace = await self._git_workspace.prepare_workspace(
            spec,
            repo_base,
            access,
        )
        diff = await self._git_workspace.build_diff(
            prepared_workspace,
            base_sha=metadata.base_sha,
            head_sha=metadata.head_sha,
        )
        return PreparedReview(
            context=PRContext(metadata=metadata, diff=diff),
            workspace=prepared_workspace,
            remote_access=access,
        )

    async def cleanup_review(
        self,
        review: PreparedReview,
    ) -> None:
        await self._git_workspace.cleanup_workspace(
            review.workspace,
            review.remote_access,
        )

    async def get_pr_metadata(self, repo_full_name: str, pr_number: int) -> PRMetadata:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{repo_full_name}/pulls/{pr_number}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
        return PRMetadata(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            title=data["title"],
            author=data["user"]["login"],
            head_sha=data["head"]["sha"],
            base_sha=data["base"]["sha"],
            head_ref=data["head"]["ref"],
            base_ref=data["base"]["ref"],
            html_url=data["html_url"],
        )

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        headers = self._headers()
        headers["Accept"] = "application/vnd.github.diff"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{repo_full_name}/pulls/{pr_number}",
                headers=headers,
            )
            response.raise_for_status()
            return response.text

    async def fetch_pr_context(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> PRContext:
        metadata = await self.get_pr_metadata(repo_full_name, pr_number)
        diff = await self.get_pr_diff(repo_full_name, pr_number)
        if head_sha and metadata.head_sha != head_sha:
            logger.warning(
                "PR head SHA mismatch: expected %s, API returned %s",
                head_sha[:7],
                metadata.head_sha[:7],
            )
        return PRContext(metadata=metadata, diff=diff)

    async def ensure_worktree(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
    ) -> Path:
        prepared_workspace = await self._git_workspace.prepare_workspace(
            spec,
            repo_base,
            self._remote_access(spec.repo_full_name),
        )
        return prepared_workspace.worktree_path

    async def publish_summary_comment(
        self,
        review: PreparedReview,
        body: str,
    ) -> ReviewCommentArtifact | None:
        return await self.post_review_comment(
            review.context.metadata.repo_full_name,
            review.context.metadata.pr_number,
            body,
        )

    async def publish_inline_comments(
        self,
        review: PreparedReview,
        comments: list[InlineComment],
        body: str = "",
    ) -> InlineCommentsResult:
        return await self.post_inline_comments(
            review.context.metadata.repo_full_name,
            review.context.metadata.pr_number,
            review.context.metadata.head_sha,
            comments,
            body=body,
            diff=review.context.diff,
        )

    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> ReviewCommentArtifact | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments",
                headers=self._headers(),
                json={"body": body},
            )
            response.raise_for_status()
            data = response.json()
        comment_id = data.get("id")
        if comment_id is None:
            return None
        return ReviewCommentArtifact(
            comment_kind="summary",
            remote_comment_id=str(comment_id),
            body=body,
        )

    def _comment_payload(
        self,
        commit_id: str,
        comment: InlineComment,
    ) -> dict:
        return {
            "commit_id": commit_id,
            "body": comment.body,
            "path": comment.path,
            "line": comment.line,
            "side": comment.side,
        }

    async def _post_inline_comment(
        self,
        client: httpx.AsyncClient,
        repo_full_name: str,
        pr_number: int,
        payload: dict,
    ) -> dict:
        response = await client.post(
            f"{self.API_BASE}/repos/{repo_full_name}/pulls/{pr_number}/comments",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def post_inline_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        comments: list[InlineComment],
        body: str = "",
        diff: str | None = None,
    ) -> InlineCommentsResult:
        if not comments:
            return InlineCommentsResult(posted=(), skipped=())

        to_post = list(comments)
        skipped: list[InlineComment] = []
        if diff:
            to_post, skipped = filter_inline_comments(comments, diff)
            for comment in skipped:
                logger.warning(
                    "Skipping inline comment on %s:%d (%s) — line not in PR diff",
                    comment.path,
                    comment.line,
                    comment.side,
                )

        if not to_post:
            return InlineCommentsResult(posted=(), skipped=tuple(skipped))

        posted: list[ReviewCommentArtifact] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for comment in to_post:
                payload = self._comment_payload(commit_id, comment)
                try:
                    data = await self._post_inline_comment(
                        client,
                        repo_full_name,
                        pr_number,
                        payload,
                    )
                    comment_id = data.get("id")
                    if comment_id is None:
                        logger.warning(
                            "Inline comment on %s:%d missing GitHub comment id",
                            comment.path,
                            comment.line,
                        )
                        continue
                    posted.append(
                        ReviewCommentArtifact(
                            comment_kind="inline",
                            remote_comment_id=str(comment_id),
                            body=comment.body,
                            path=comment.path,
                            line=comment.line,
                            side=comment.side,
                            finding_index=comment.finding_index,
                        )
                    )
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 422:
                        logger.warning(
                            "Skipping inline comment on %s:%d — GitHub 422: %s",
                            comment.path,
                            comment.line,
                            exc.response.text,
                        )
                        skipped.append(comment)
                        continue
                    raise

        return InlineCommentsResult(
            posted=tuple(posted),
            skipped=tuple(skipped),
        )
