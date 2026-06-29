import base64
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from coreview_shared.git.diff_lines import filter_inline_comments
from coreview_shared.git.models import (
    InlineComment,
    InlineCommentsResult,
    PreparedReview,
    RemoteRepoAccess,
    WebhookEvent,
)
from coreview_shared.review import PRContext, PRMetadata
from coreview_shared.workspace.adapter import GitWorkspaceAdapter
from coreview_shared.workspace.models import WorkspaceSpec
from coreview_shared.workspace.protocol import CommandRunner

logger = logging.getLogger(__name__)

HANDLED_WEBHOOK_EVENTS = frozenset({"pr:opened", "pr:from_ref_updated", "pr:reopened"})


def parse_repo_full_name(repo_full_name: str) -> tuple[str, str]:
    parts = [part.strip() for part in repo_full_name.split("/", maxsplit=1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        msg = f"Invalid Bitbucket DC repo_full_name: {repo_full_name!r}"
        raise ValueError(msg)
    return parts[0], parts[1]


def normalize_base_url(base_url: str) -> str:
    return base_url.strip().rstrip("/")


class BitbucketDataCenterProvider:
    def __init__(
        self,
        token: str,
        *,
        base_url: str,
        workspace_adapter: GitWorkspaceAdapter | None = None,
    ) -> None:
        self._token = token
        self._base_url = normalize_base_url(base_url)
        self._workspace_adapter = workspace_adapter or GitWorkspaceAdapter()

    def _api_base(self) -> str:
        return f"{self._base_url}/rest/api/latest"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _pr_api_url(
        self,
        project_key: str,
        repo_slug: str,
        pr_number: int,
        suffix: str = "",
    ) -> str:
        return (
            f"{self._api_base()}/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_number}{suffix}"
        )

    def _clone_url(self, project_key: str, repo_slug: str) -> str:
        parsed = urlparse(self._base_url)
        host = parsed.netloc or parsed.path
        return f"https://{self._token}@{host}/scm/{project_key}/{repo_slug}.git"

    def _remote_access(self, repo_full_name: str) -> RemoteRepoAccess:
        project_key, repo_slug = parse_repo_full_name(repo_full_name)
        return RemoteRepoAccess(clone_url=self._clone_url(project_key, repo_slug))

    def build_pr_url(self, repo_full_name: str, pr_number: int) -> str:
        project_key, repo_slug = parse_repo_full_name(repo_full_name)
        return (
            f"{self._base_url}/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_number}"
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
        project_key, repo_slug = parse_repo_full_name(repo_full_name)
        base = (
            f"{self._base_url}/projects/{project_key}/repos/{repo_slug}"
            f"/browse/{file_path}?at={ref}"
        )
        return f"{base}#{line}" if line else base

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str | None,
        secret: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bool:
        del headers, payload
        if not secret or ":" not in secret:
            return False
        if not signature or not signature.lower().startswith("basic "):
            return False

        expected_user, expected_pass = secret.split(":", 1)
        if not expected_user or not expected_pass:
            return False

        try:
            decoded = base64.b64decode(signature.split(" ", 1)[1].strip()).decode()
        except (ValueError, UnicodeDecodeError):
            return False

        if ":" not in decoded:
            return False
        user, password = decoded.split(":", 1)
        return user == expected_user and password == expected_pass

    def parse_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookEvent | None:
        normalized = {k.lower(): v for k, v in headers.items()}
        event_key = normalized.get("x-event-key", "")
        if event_key not in HANDLED_WEBHOOK_EVENTS:
            return None

        payload = json.loads(body)
        pull_request = payload.get("pullRequest")
        if not isinstance(pull_request, dict):
            return None

        if pull_request.get("state") != "OPEN":
            return None

        to_ref = pull_request.get("toRef")
        from_ref = pull_request.get("fromRef")
        if not isinstance(to_ref, dict) or not isinstance(from_ref, dict):
            return None

        repository = to_ref.get("repository")
        project = repository.get("project", {}) if isinstance(repository, dict) else {}
        project_key = project.get("key", "") if isinstance(project, dict) else ""
        repo_slug = repository.get("slug", "") if isinstance(repository, dict) else ""
        if not project_key or not repo_slug:
            return None

        pr_id = pull_request.get("id")
        latest_commit = from_ref.get("latestCommit", "")
        if pr_id is None or not latest_commit:
            return None

        repo_full_name = f"{project_key}/{repo_slug}"
        pr_url = pull_request.get("links", {}).get("self", [{}])
        if isinstance(pr_url, list) and pr_url:
            href = pr_url[0].get("href", "") if isinstance(pr_url[0], dict) else ""
        else:
            href = ""
        if not href:
            href = self.build_pr_url(repo_full_name, int(pr_id))

        delivery_id = normalized.get("x-request-id") or str(pr_id)

        return WebhookEvent(
            event_type=event_key,
            action=event_key.rsplit(":", maxsplit=1)[-1],
            repo_full_name=repo_full_name,
            pr_number=int(pr_id),
            head_sha=latest_commit,
            delivery_id=delivery_id,
            pr_title=pull_request.get("title") or "",
            pr_url=href,
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
        project_key, repo_slug = parse_repo_full_name(repo_full_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self._pr_api_url(project_key, repo_slug, pr_number),
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        from_ref = data.get("fromRef", {})
        to_ref = data.get("toRef", {})
        author = data.get("author", {})
        author_name = (
            author.get("displayName", "unknown")
            if isinstance(author, dict)
            else "unknown"
        )
        html_url = self.build_pr_url(repo_full_name, pr_number)
        links = data.get("links")
        if isinstance(links, dict):
            self_link = links.get("self")
            if isinstance(self_link, list) and self_link:
                href = self_link[0].get("href", "")
                if href:
                    html_url = href

        return PRMetadata(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            title=data.get("title", ""),
            author=author_name,
            head_sha=from_ref.get("latestCommit", "")
            if isinstance(from_ref, dict)
            else "",
            base_sha=to_ref.get("latestCommit", "") if isinstance(to_ref, dict) else "",
            head_ref=from_ref.get("displayId", "")
            if isinstance(from_ref, dict)
            else "",
            base_ref=to_ref.get("displayId", "") if isinstance(to_ref, dict) else "",
            html_url=html_url,
        )

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        del repo_full_name, pr_number
        return ""

    async def fetch_pr_context(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> PRContext:
        metadata = await self.get_pr_metadata(repo_full_name, pr_number)
        if head_sha and metadata.head_sha != head_sha:
            logger.warning(
                "PR head SHA mismatch: expected %s, API returned %s",
                head_sha[:7],
                metadata.head_sha[:7],
            )
        return PRContext(metadata=metadata, diff="")

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
            base_sha=review.context.metadata.base_sha,
        )

    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> None:
        project_key, repo_slug = parse_repo_full_name(repo_full_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._pr_api_url(project_key, repo_slug, pr_number, "/comments"),
                headers=self._headers(),
                json={"text": body},
            )
            response.raise_for_status()

    def _anchor_payload(
        self,
        comment: InlineComment,
        *,
        from_hash: str,
        to_hash: str,
        body: str,
    ) -> dict:
        line_type = "REMOVED" if comment.side == "LEFT" else "ADDED"
        file_type = "FROM" if comment.side == "LEFT" else "TO"
        return {
            "text": body or comment.body,
            "anchor": {
                "diffType": "COMMIT",
                "fromHash": from_hash,
                "toHash": to_hash,
                "path": comment.path,
                "srcPath": comment.path,
                "line": comment.line,
                "lineType": line_type,
                "fileType": file_type,
            },
        }

    async def post_inline_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        comments: list[InlineComment],
        body: str = "",
        diff: str | None = None,
        *,
        base_sha: str = "",
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

        metadata = await self.get_pr_metadata(repo_full_name, pr_number)
        from_hash = base_sha or metadata.base_sha
        to_hash = metadata.head_sha
        project_key, repo_slug = parse_repo_full_name(repo_full_name)

        posted: list[InlineComment] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for comment in to_post:
                payload = self._anchor_payload(
                    comment,
                    from_hash=from_hash,
                    to_hash=to_hash,
                    body=body,
                )
                try:
                    response = await client.post(
                        self._pr_api_url(
                            project_key, repo_slug, pr_number, "/comments"
                        ),
                        headers=self._headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    posted.append(comment)
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Skipping inline comment on %s:%d — Bitbucket DC %s: %s",
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
