import hashlib
import hmac
import json
import logging
from pathlib import Path

import httpx

from coreview_shared.protocols import (
    CommandRunner,
    InlineComment,
    InlineCommentsResult,
    PRContext,
    PreparedReview,
    PRMetadata,
    RemoteRepoAccess,
    WebhookEvent,
    WorkspaceSpec,
)
from coreview_shared.providers.git.diff_lines import filter_inline_comments
from coreview_shared.workspace import GitWorkspaceAdapter

logger = logging.getLogger(__name__)

API_BASE = "https://api.bitbucket.org/2.0"
HANDLED_WEBHOOK_EVENTS = frozenset({"pullrequest:created", "pullrequest:updated"})


def parse_repo_full_name(repo_full_name: str) -> tuple[str, str]:
    parts = [part.strip() for part in repo_full_name.split("/", maxsplit=1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        msg = f"Invalid Bitbucket repo_full_name: {repo_full_name!r}"
        raise ValueError(msg)
    return parts[0], parts[1]


class BitbucketCloudProvider:
    def __init__(
        self,
        token: str,
        *,
        workspace_adapter: GitWorkspaceAdapter | None = None,
    ) -> None:
        self._token = token
        self._workspace_adapter = workspace_adapter or GitWorkspaceAdapter()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _pr_url(self, repo_full_name: str, pr_number: int, suffix: str = "") -> str:
        workspace, repo_slug = parse_repo_full_name(repo_full_name)
        return (
            f"{API_BASE}/repositories/{workspace}/{repo_slug}"
            f"/pullrequests/{pr_number}{suffix}"
        )

    def _clone_url(self, repo_full_name: str) -> str:
        workspace, repo_slug = parse_repo_full_name(repo_full_name)
        return (
            f"https://x-token-auth:{self._token}@bitbucket.org/"
            f"{workspace}/{repo_slug}.git"
        )

    def _remote_access(self, repo_full_name: str) -> RemoteRepoAccess:
        return RemoteRepoAccess(clone_url=self._clone_url(repo_full_name))

    def build_pr_url(self, repo_full_name: str, pr_number: int) -> str:
        workspace, repo_slug = parse_repo_full_name(repo_full_name)
        return (
            f"https://bitbucket.org/{workspace}/{repo_slug}/pull-requests/{pr_number}"
        )

    def build_blob_url(
        self,
        repo_full_name: str,
        ref: str,
        file_path: str,
        line: int | None = None,
    ) -> str | None:
        if not file_path.strip():
            return None
        workspace, repo_slug = parse_repo_full_name(repo_full_name)
        base = f"https://bitbucket.org/{workspace}/{repo_slug}/src/{ref}/{file_path}"
        return f"{base}#lines-{line}" if line else base

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str | None,
        secret: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bool:
        del headers
        if not secret or not signature:
            return False
        for prefix, digestmod in (("sha256=", hashlib.sha256), ("sha1=", hashlib.sha1)):
            if signature.startswith(prefix):
                expected = hmac.new(
                    secret.encode(),
                    payload,
                    digestmod,
                ).hexdigest()
                return hmac.compare_digest(signature.removeprefix(prefix), expected)
        return False

    def parse_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookEvent | None:
        normalized = {k.lower(): v for k, v in headers.items()}
        event_key = normalized.get("x-event-key", "")
        if event_key not in HANDLED_WEBHOOK_EVENTS:
            return None

        payload = json.loads(body)
        pullrequest = payload.get("pullrequest")
        repository = payload.get("repository")
        if not isinstance(pullrequest, dict) or not isinstance(repository, dict):
            return None

        if pullrequest.get("draft"):
            return None

        repo_full_name = repository.get("full_name", "")
        pr_id = pullrequest.get("id")
        source = pullrequest.get("source")
        if not repo_full_name or pr_id is None or not isinstance(source, dict):
            return None

        commit = source.get("commit")
        head_sha = commit.get("hash", "") if isinstance(commit, dict) else ""
        if not head_sha:
            return None

        pr_url = ""
        links = pullrequest.get("links")
        if isinstance(links, dict):
            html = links.get("html")
            if isinstance(html, dict):
                pr_url = html.get("href", "") or ""
        if not pr_url:
            pr_url = self.build_pr_url(repo_full_name, int(pr_id))

        delivery_id = normalized.get("x-hook-uuid") or normalized.get("x-request-uuid")

        return WebhookEvent(
            event_type=event_key,
            action=event_key.rsplit(":", maxsplit=1)[-1],
            repo_full_name=repo_full_name,
            pr_number=int(pr_id),
            head_sha=head_sha,
            delivery_id=delivery_id,
            pr_title=pullrequest.get("title") or "",
            pr_url=pr_url,
        )

    async def prepare_review(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
        runner: CommandRunner,
    ) -> PreparedReview:
        metadata = await self.get_pr_metadata(spec.repo_full_name, spec.pr_number)
        if spec.head_sha and metadata.head_sha != spec.head_sha:
            logger.warning(
                "PR head SHA mismatch: expected %s, API returned %s",
                spec.head_sha[:7],
                metadata.head_sha[:7],
            )

        access = self._remote_access(spec.repo_full_name)
        prepared_workspace = await self._workspace_adapter.prepare_workspace(
            spec,
            repo_base,
            runner,
            access,
        )
        diff = await self._workspace_adapter.build_diff(
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
        runner: CommandRunner,
    ) -> None:
        await self._workspace_adapter.cleanup_workspace(
            review.workspace,
            runner,
            review.remote_access,
        )

    async def get_pr_metadata(self, repo_full_name: str, pr_number: int) -> PRMetadata:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self._pr_url(repo_full_name, pr_number),
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        source = data.get("source", {})
        destination = data.get("destination", {})
        source_commit = source.get("commit", {}) if isinstance(source, dict) else {}
        dest_commit = (
            destination.get("commit", {}) if isinstance(destination, dict) else {}
        )
        source_branch = source.get("branch", {}) if isinstance(source, dict) else {}
        dest_branch = (
            destination.get("branch", {}) if isinstance(destination, dict) else {}
        )
        author = data.get("author", {})
        author_name = (
            author.get("display_name", "unknown")
            if isinstance(author, dict)
            else "unknown"
        )
        html_url = ""
        links = data.get("links")
        if isinstance(links, dict):
            html = links.get("html")
            if isinstance(html, dict):
                html_url = html.get("href", "") or ""
        if not html_url:
            html_url = self.build_pr_url(repo_full_name, pr_number)

        return PRMetadata(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            title=data.get("title", ""),
            author=author_name,
            head_sha=source_commit.get("hash", "")
            if isinstance(source_commit, dict)
            else "",
            base_sha=dest_commit.get("hash", "")
            if isinstance(dest_commit, dict)
            else "",
            head_ref=source_branch.get("name", "")
            if isinstance(source_branch, dict)
            else "",
            base_ref=dest_branch.get("name", "")
            if isinstance(dest_branch, dict)
            else "",
            html_url=html_url,
        )

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                self._pr_url(repo_full_name, pr_number, "/diff"),
                headers=self._headers(),
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
        runner: CommandRunner,
    ) -> Path:
        prepared_workspace = await self._workspace_adapter.prepare_workspace(
            spec,
            repo_base,
            runner,
            self._remote_access(spec.repo_full_name),
        )
        return prepared_workspace.worktree_path

    async def publish_summary_comment(
        self,
        review: PreparedReview,
        body: str,
    ) -> None:
        await self.post_review_comment(
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
    ) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._pr_url(repo_full_name, pr_number, "/comments"),
                headers=self._headers(),
                json={"content": {"raw": body}},
            )
            response.raise_for_status()

    def _inline_payload(self, comment: InlineComment, body: str) -> dict:
        inline: dict[str, object] = {"path": comment.path}
        if comment.side == "LEFT":
            inline["from"] = comment.line
        else:
            inline["to"] = comment.line
        return {
            "content": {"raw": body or comment.body},
            "inline": inline,
        }

    async def post_inline_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        comments: list[InlineComment],
        body: str = "",
        diff: str | None = None,
    ) -> InlineCommentsResult:
        del commit_id
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

        posted: list[InlineComment] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for comment in to_post:
                payload = self._inline_payload(comment, body)
                try:
                    response = await client.post(
                        self._pr_url(repo_full_name, pr_number, "/comments"),
                        headers=self._headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    posted.append(comment)
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Skipping inline comment on %s:%d — Bitbucket %s: %s",
                        comment.path,
                        comment.line,
                        exc.response.status_code,
                        exc.response.text,
                    )
                    skipped.append(comment)

        return InlineCommentsResult(
            posted=tuple(posted),
            skipped=tuple(skipped),
        )
