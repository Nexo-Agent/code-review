import hashlib
import hmac
import json
import logging

import httpx

from app.providers.git.diff_lines import filter_inline_comments
from app.providers.protocols import (
    CommandRunner,
    InlineComment,
    InlineCommentsResult,
    PRContext,
    PRMetadata,
    WebhookEvent,
    Workspace,
    WorkspaceSpec,
)

logger = logging.getLogger(__name__)

HANDLED_WEBHOOK_ACTIONS = frozenset({"opened", "synchronize", "reopened"})


class GitHubProvider:
    API_BASE = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._token = token

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

    def verify_webhook_signature(
        self, payload: bytes, signature: str | None, secret: str
    ) -> bool:
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

        return WebhookEvent(
            event_type=event_type,
            action=action,
            repo_full_name=repo["full_name"],
            pr_number=pr["number"],
            head_sha=pr["head"]["sha"],
            delivery_id=normalized.get("x-github-delivery"),
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

    async def clone_repository(
        self,
        spec: WorkspaceSpec,
        workspace: Workspace,
        runner: CommandRunner,
    ) -> None:
        clone_url = self._clone_url(spec.repo_full_name)
        await runner.run(
            ["git", "clone", "--depth", "1", clone_url, "repo"],
            cwd=workspace.path,
        )
        repo_path = workspace.path / "repo"
        await runner.run(
            ["git", "fetch", "origin", spec.head_sha],
            cwd=repo_path,
        )
        await runner.run(
            ["git", "checkout", spec.head_sha],
            cwd=repo_path,
        )

    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments",
                headers=self._headers(),
                json={"body": body},
            )
            response.raise_for_status()

    def _review_payload(
        self,
        commit_id: str,
        comments: list[InlineComment],
        body: str,
    ) -> dict:
        return {
            "commit_id": commit_id,
            "body": body,
            "event": "COMMENT",
            "comments": [
                {
                    "path": c.path,
                    "line": c.line,
                    "side": c.side,
                    "body": c.body,
                }
                for c in comments
            ],
        }

    async def _post_review(
        self,
        client: httpx.AsyncClient,
        repo_full_name: str,
        pr_number: int,
        payload: dict,
    ) -> None:
        response = await client.post(
            f"{self.API_BASE}/repos/{repo_full_name}/pulls/{pr_number}/reviews",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()

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

        posted: list[InlineComment] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            batch_payload = self._review_payload(commit_id, to_post, body)
            try:
                await self._post_review(
                    client, repo_full_name, pr_number, batch_payload
                )
                posted.extend(to_post)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 422:
                    raise
                logger.warning(
                    "Batch inline review returned 422, "
                    "posting comments individually: %s",
                    exc.response.text,
                )
                for comment in to_post:
                    single_payload = self._review_payload(commit_id, [comment], body)
                    try:
                        await self._post_review(
                            client, repo_full_name, pr_number, single_payload
                        )
                        posted.append(comment)
                    except httpx.HTTPStatusError as single_exc:
                        if single_exc.response.status_code == 422:
                            logger.warning(
                                "Skipping inline comment on %s:%d — GitHub 422: %s",
                                comment.path,
                                comment.line,
                                single_exc.response.text,
                            )
                            skipped.append(comment)
                            continue
                        raise

        return InlineCommentsResult(
            posted=tuple(posted),
            skipped=tuple(skipped),
        )
