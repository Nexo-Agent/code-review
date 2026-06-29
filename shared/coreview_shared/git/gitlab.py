import base64
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

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

DEFAULT_GITLAB_BASE_URL = "https://gitlab.com"
HANDLED_WEBHOOK_ACTIONS = frozenset({"open", "reopen"})
WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300


def verify_gitlab_signing_token(
    payload: bytes,
    signing_token: str,
    *,
    message_id: str,
    timestamp: str,
    received_signatures: str,
    now: float | None = None,
) -> bool:
    if not signing_token.startswith("whsec_"):
        return False
    try:
        raw_key = base64.b64decode(signing_token.removeprefix("whsec_"))
    except ValueError:
        return False

    try:
        ts = int(timestamp)
    except ValueError:
        return False
    current = now if now is not None else time.time()
    if abs(current - ts) > WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
        return False

    body_text = payload.decode("utf-8")
    message = f"{message_id}.{timestamp}.{body_text}".encode()
    digest = hmac.new(raw_key, message, hashlib.sha256).digest()
    expected = "v1," + base64.b64encode(digest).decode("utf-8")

    for sig in received_signatures.split():
        candidate = sig.strip().strip('"')
        if hmac.compare_digest(expected, candidate):
            return True
    return False


def normalize_gitlab_base_url(base_url: str) -> str:
    trimmed = base_url.strip().rstrip("/")
    return trimmed or DEFAULT_GITLAB_BASE_URL


def parse_repo_full_name(repo_full_name: str) -> str:
    path = repo_full_name.strip().strip("/")
    if not path or "/" not in path:
        msg = f"Invalid GitLab repo_full_name: {repo_full_name!r}"
        raise ValueError(msg)
    return path


@dataclass(frozen=True, slots=True)
class GitLabDiffRefs:
    base_sha: str
    head_sha: str
    start_sha: str


class GitLabProvider:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_GITLAB_BASE_URL,
        workspace_adapter: GitWorkspaceAdapter | None = None,
    ) -> None:
        self._token = token
        self._base_url = normalize_gitlab_base_url(base_url)
        self._workspace_adapter = workspace_adapter or GitWorkspaceAdapter()
        self._diff_refs_cache: dict[tuple[str, int], GitLabDiffRefs] = {}

    def _api_base(self) -> str:
        return f"{self._base_url}/api/v4"

    def _encode_project(self, path_with_namespace: str) -> str:
        return quote(parse_repo_full_name(path_with_namespace), safe="")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["PRIVATE-TOKEN"] = self._token
        return headers

    def _clone_url(self, path_with_namespace: str) -> str:
        path = parse_repo_full_name(path_with_namespace)
        parsed = urlparse(self._base_url)
        host = parsed.netloc or parsed.path
        return f"https://oauth2:{self._token}@{host}/{path}.git"

    def _remote_access(self, repo_full_name: str) -> RemoteRepoAccess:
        return RemoteRepoAccess(clone_url=self._clone_url(repo_full_name))

    def build_pr_url(self, repo_full_name: str, pr_number: int) -> str:
        path = parse_repo_full_name(repo_full_name)
        return f"{self._base_url}/{path}/-/merge_requests/{pr_number}"

    def build_blob_url(
        self,
        repo_full_name: str,
        ref: str,
        file_path: str,
        line: int | None = None,
    ) -> str | None:
        if not file_path.strip():
            return None
        path = parse_repo_full_name(repo_full_name)
        base = f"{self._base_url}/{path}/-/blob/{ref}/{file_path}"
        return f"{base}#L{line}" if line else base

    def _mr_url(self, path_with_namespace: str, mr_iid: int, suffix: str = "") -> str:
        project = self._encode_project(path_with_namespace)
        base = f"{self._api_base()}/projects/{project}/merge_requests/{mr_iid}"
        return f"{base}{suffix}"

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str | None,
        secret: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bool:
        if not secret:
            return False

        normalized = {k.lower(): v for k, v in (headers or {}).items()}

        if secret.startswith("whsec_"):
            webhook_signature = signature or normalized.get("webhook-signature")
            message_id = normalized.get("webhook-id")
            timestamp = normalized.get("webhook-timestamp")
            if not webhook_signature or not message_id or not timestamp:
                return False
            return verify_gitlab_signing_token(
                payload,
                secret,
                message_id=message_id,
                timestamp=timestamp,
                received_signatures=webhook_signature,
            )

        token = signature or normalized.get("x-gitlab-token")
        if not token:
            return False
        return hmac.compare_digest(token, secret)

    def _should_handle_update(self, object_attributes: dict) -> bool:
        if object_attributes.get("action") != "update":
            return False
        if object_attributes.get("oldrev"):
            return True
        changes = object_attributes.get("changes")
        if isinstance(changes, dict) and changes.get("oldrev"):
            return True
        return False

    def parse_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookEvent | None:
        normalized = {k.lower(): v for k, v in headers.items()}
        payload = json.loads(body)
        if payload.get("object_kind") != "merge_request":
            return None

        object_attributes = payload.get("object_attributes")
        project = payload.get("project")
        if not isinstance(object_attributes, dict) or not isinstance(project, dict):
            return None

        action = object_attributes.get("action", "")
        if action not in HANDLED_WEBHOOK_ACTIONS and not self._should_handle_update(
            object_attributes
        ):
            return None

        if object_attributes.get("draft") or object_attributes.get("work_in_progress"):
            return None

        path_with_namespace = project.get("path_with_namespace", "")
        mr_iid = object_attributes.get("iid")
        last_commit = object_attributes.get("last_commit")
        head_sha = ""
        if isinstance(last_commit, dict):
            head_sha = last_commit.get("id", "")

        if not path_with_namespace or not mr_iid or not head_sha:
            return None

        delivery_id = normalized.get("webhook-id") or normalized.get(
            "x-gitlab-event-uuid"
        )
        if not delivery_id:
            delivery_id = str(object_attributes.get("id", "")) or None

        pr_url = object_attributes.get("url") or ""
        if not pr_url:
            pr_url = self.build_pr_url(path_with_namespace, int(mr_iid))

        return WebhookEvent(
            event_type="merge_request",
            action=action,
            repo_full_name=path_with_namespace,
            pr_number=int(mr_iid),
            head_sha=head_sha,
            delivery_id=delivery_id,
            pr_title=object_attributes.get("title") or "",
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
                "MR head SHA mismatch: expected %s, API returned %s",
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

    def _parse_diff_refs(self, data: dict) -> GitLabDiffRefs:
        diff_refs = data.get("diff_refs")
        if not isinstance(diff_refs, dict):
            msg = "GitLab merge request response missing diff_refs"
            raise ValueError(msg)
        base_sha = diff_refs.get("base_sha", "")
        head_sha = diff_refs.get("head_sha", "")
        start_sha = diff_refs.get("start_sha", "")
        if not base_sha or not head_sha or not start_sha:
            msg = "GitLab merge request diff_refs incomplete"
            raise ValueError(msg)
        return GitLabDiffRefs(
            base_sha=base_sha,
            head_sha=head_sha,
            start_sha=start_sha,
        )

    async def _get_diff_refs(
        self, repo_full_name: str, pr_number: int
    ) -> GitLabDiffRefs:
        cache_key = (repo_full_name, pr_number)
        cached = self._diff_refs_cache.get(cache_key)
        if cached:
            return cached

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self._mr_url(repo_full_name, pr_number),
                headers=self._headers(),
            )
            response.raise_for_status()
            diff_refs = self._parse_diff_refs(response.json())

        self._diff_refs_cache[cache_key] = diff_refs
        return diff_refs

    async def get_pr_metadata(self, repo_full_name: str, pr_number: int) -> PRMetadata:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self._mr_url(repo_full_name, pr_number),
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        diff_refs = self._parse_diff_refs(data)
        cache_key = (repo_full_name, pr_number)
        self._diff_refs_cache[cache_key] = diff_refs

        author = data.get("author", {})
        author_name = (
            author.get("username", "unknown") if isinstance(author, dict) else "unknown"
        )
        return PRMetadata(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            title=data.get("title", ""),
            author=author_name,
            head_sha=diff_refs.head_sha,
            base_sha=diff_refs.base_sha,
            head_ref=data.get("source_branch", ""),
            base_ref=data.get("target_branch", ""),
            html_url=data.get("web_url", ""),
        )

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        headers = self._headers()
        headers["Accept"] = "application/json"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                self._mr_url(repo_full_name, pr_number, "/changes"),
                headers=headers,
            )
            response.raise_for_status()
            changes = response.json().get("changes", [])
        if not changes:
            return ""
        parts: list[str] = []
        for change in changes:
            if not isinstance(change, dict):
                continue
            diff = change.get("diff")
            if isinstance(diff, str) and diff:
                parts.append(diff)
        return "\n".join(parts)

    async def fetch_pr_context(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> PRContext:
        metadata = await self.get_pr_metadata(repo_full_name, pr_number)
        diff = await self.get_pr_diff(repo_full_name, pr_number)
        if head_sha and metadata.head_sha != head_sha:
            logger.warning(
                "MR head SHA mismatch: expected %s, API returned %s",
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
                self._mr_url(repo_full_name, pr_number, "/notes"),
                headers=self._headers(),
                json={"body": body},
            )
            response.raise_for_status()

    def _discussion_payload(
        self,
        comment: InlineComment,
        diff_refs: GitLabDiffRefs,
        body: str,
    ) -> dict:
        position: dict[str, str | int] = {
            "position_type": "text",
            "base_sha": diff_refs.base_sha,
            "head_sha": diff_refs.head_sha,
            "start_sha": diff_refs.start_sha,
            "new_path": comment.path,
            "old_path": comment.path,
        }
        if comment.side == "LEFT":
            position["old_line"] = comment.line
        else:
            position["new_line"] = comment.line
        return {"body": body or comment.body, "position": position}

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
                    "Skipping inline comment on %s:%d (%s) — line not in MR diff",
                    comment.path,
                    comment.line,
                    comment.side,
                )

        if not to_post:
            return InlineCommentsResult(posted=(), skipped=tuple(skipped))

        diff_refs = await self._get_diff_refs(repo_full_name, pr_number)
        posted: list[InlineComment] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for comment in to_post:
                payload = self._discussion_payload(comment, diff_refs, body)
                try:
                    response = await client.post(
                        self._mr_url(repo_full_name, pr_number, "/discussions"),
                        headers=self._headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    posted.append(comment)
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Skipping inline comment on %s:%d — GitLab %s: %s",
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
