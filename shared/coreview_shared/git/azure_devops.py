import base64
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

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
from coreview_shared.workspace import GitWorkspaceAdapter

logger = logging.getLogger(__name__)

API_VERSION = "7.1"
HANDLED_WEBHOOK_EVENTS = frozenset(
    {"git.pullrequest.created", "git.pullrequest.updated"}
)


def parse_repo_full_name(
    repo_full_name: str,
    *,
    organization: str = "",
    project: str = "",
) -> tuple[str, str, str]:
    parts = [part.strip() for part in repo_full_name.split("/") if part.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if organization.strip() and project.strip() and parts:
        return organization.strip(), project.strip(), parts[-1]
    if len(parts) == 2 and organization.strip():
        return organization.strip(), parts[0], parts[1]
    msg = f"Invalid Azure DevOps repo_full_name: {repo_full_name!r}"
    raise ValueError(msg)


def _organization_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url.rstrip("/"))
    segments = [segment for segment in parsed.path.split("/") if segment]
    if parsed.netloc and "dev.azure.com" in parsed.netloc and segments:
        return segments[0]
    if parsed.netloc:
        return parsed.netloc.split(".")[0]
    return ""


def _ref_to_branch(ref: str) -> str:
    prefix = "refs/heads/"
    if ref.startswith(prefix):
        return ref[len(prefix) :]
    return ref


class AzureDevOpsProvider:
    def __init__(
        self,
        *,
        pat: str,
        organization: str = "",
        project: str = "",
        workspace_adapter: GitWorkspaceAdapter | None = None,
    ) -> None:
        self._pat = pat
        self._organization = organization
        self._project = project
        self._repository_ids: dict[str, str] = {}
        self._workspace_adapter = workspace_adapter or GitWorkspaceAdapter()

    def _auth_headers(self) -> dict[str, str]:
        token = base64.b64encode(f":{self._pat}".encode()).decode()
        return {
            "Accept": "application/json",
            "Authorization": f"Basic {token}",
        }

    def _api_url(self, organization: str, project: str, path: str) -> str:
        base = f"https://dev.azure.com/{organization}"
        if project:
            return f"{base}/{project}/_apis{path}?api-version={API_VERSION}"
        return f"{base}/_apis{path}?api-version={API_VERSION}"

    def _repo_cache_key(self, organization: str, project: str, repo: str) -> str:
        return f"{organization}/{project}/{repo}"

    def _remote_access(self, repo_full_name: str) -> RemoteRepoAccess:
        organization, project, repo = parse_repo_full_name(
            repo_full_name,
            organization=self._organization,
            project=self._project,
        )
        clone_url = f"https://dev.azure.com/{organization}/{project}/_git/{repo}"
        return RemoteRepoAccess(
            clone_url=clone_url,
            auth_args=tuple(self._git_auth_args()),
        )

    async def _resolve_repository_id(
        self,
        client: httpx.AsyncClient,
        organization: str,
        project: str,
        repo: str,
    ) -> str:
        cache_key = self._repo_cache_key(organization, project, repo)
        cached = self._repository_ids.get(cache_key)
        if cached:
            return cached

        response = await client.get(
            self._api_url(organization, project, f"/git/repositories/{repo}"),
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        repository_id = response.json()["id"]
        self._repository_ids[cache_key] = repository_id
        return repository_id

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str | None,
        secret: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bool:
        del headers
        del payload
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
        del headers
        payload = json.loads(body)
        event_type = payload.get("eventType", "")
        if event_type not in HANDLED_WEBHOOK_EVENTS:
            return None

        resource = payload.get("resource")
        if not isinstance(resource, dict):
            return None

        if resource.get("status") != "active":
            return None

        repository = resource.get("repository")
        if not isinstance(repository, dict):
            return None

        project = repository.get("project")
        if not isinstance(project, dict):
            return None

        containers = payload.get("resourceContainers", {})
        account = containers.get("account", {})
        base_url = account.get("baseUrl", "") if isinstance(account, dict) else ""
        organization = _organization_from_base_url(base_url)
        if not organization:
            return None

        repo_name = repository.get("name", "")
        project_name = project.get("name", "")
        if not repo_name or not project_name:
            return None

        pull_request_id = resource.get("pullRequestId")
        source_commit = resource.get("lastMergeSourceCommit", {})
        head_sha = (
            source_commit.get("commitId", "") if isinstance(source_commit, dict) else ""
        )
        if not pull_request_id or not head_sha:
            return None

        repo_id = repository.get("id")
        if isinstance(repo_id, str) and repo_id:
            cache_key = self._repo_cache_key(organization, project_name, repo_name)
            self._repository_ids[cache_key] = repo_id

        repo_full_name = f"{organization}/{project_name}/{repo_name}"
        pr_number = int(pull_request_id)
        pr_url = resource.get("url") or ""
        if not pr_url:
            pr_url = self.build_pr_url(repo_full_name, pr_number)

        return WebhookEvent(
            event_type=event_type,
            action=event_type.rsplit(".", maxsplit=1)[-1],
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
            delivery_id=payload.get("id"),
            pr_title=resource.get("title") or "",
            pr_url=pr_url,
        )

    def build_pr_url(self, repo_full_name: str, pr_number: int) -> str:
        organization, project, repo = parse_repo_full_name(
            repo_full_name,
            organization=self._organization,
            project=self._project,
        )
        return (
            f"https://dev.azure.com/{organization}/{project}/_git/{repo}"
            f"/pullrequest/{pr_number}"
        )

    def build_blob_url(
        self,
        repo_full_name: str,
        ref: str,
        file_path: str,
        line: int | None = None,
    ) -> str | None:
        del ref, file_path, line
        return None

    async def prepare_review(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
        runner: CommandRunner,
    ) -> PreparedReview:
        """Prepare Azure DevOps review inputs without leaking provider branches.

        Azure DevOps does not currently provide the same simple diff shape as
        GitHub for this project, so the provider still fetches metadata from the
        API but delegates diff generation to the shared local git adapter.
        """

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
        organization, project, repo = parse_repo_full_name(
            repo_full_name,
            organization=self._organization,
            project=self._project,
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self._api_url(organization, project, f"/git/pullrequests/{pr_number}"),
                headers=self._auth_headers(),
            )
            response.raise_for_status()
            data = response.json()

        source_commit = data.get("lastMergeSourceCommit", {})
        target_commit = data.get("lastMergeTargetCommit", {})
        created_by = data.get("createdBy", {})
        repository = data.get("repository", {})
        if isinstance(repository, dict):
            repo_id = repository.get("id")
            if isinstance(repo_id, str) and repo_id:
                cache_key = self._repo_cache_key(organization, project, repo)
                self._repository_ids[cache_key] = repo_id

        head_sha = (
            source_commit.get("commitId", "") if isinstance(source_commit, dict) else ""
        )
        base_sha = (
            target_commit.get("commitId", "") if isinstance(target_commit, dict) else ""
        )
        author = (
            created_by.get("displayName", "unknown")
            if isinstance(created_by, dict)
            else "unknown"
        )
        html_url = data.get("url", "")
        if not html_url:
            html_url = (
                f"https://dev.azure.com/{organization}/{project}/_git/{repo}"
                f"/pullrequest/{pr_number}"
            )

        return PRMetadata(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            title=data.get("title", ""),
            author=author,
            head_sha=head_sha,
            base_sha=base_sha,
            head_ref=_ref_to_branch(data.get("sourceRefName", "")),
            base_ref=_ref_to_branch(data.get("targetRefName", "")),
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

    def _git_auth_args(self) -> list[str]:
        auth_token = base64.b64encode(f":{self._pat}".encode()).decode()
        return ["-c", f"http.extraheader=Authorization: Basic {auth_token}"]

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

    async def build_diff_from_workspace(
        self,
        runner: CommandRunner,
        repo_path: Path,
        base_sha: str,
        head_sha: str,
    ) -> str:
        del runner
        import asyncio
        import subprocess

        def _run_diff() -> str:
            result = subprocess.run(
                ["git", "diff", f"{base_sha}..{head_sha}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                output = result.stderr or result.stdout or ""
                msg = f"git diff failed ({result.returncode}): {output}"
                raise RuntimeError(msg)
            return result.stdout

        return await asyncio.to_thread(_run_diff)

    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> None:
        organization, project, repo = parse_repo_full_name(
            repo_full_name,
            organization=self._organization,
            project=self._project,
        )
        payload = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": body,
                    "commentType": 1,
                }
            ],
            "status": 1,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            repository_id = await self._resolve_repository_id(
                client, organization, project, repo
            )
            response = await client.post(
                self._api_url(
                    organization,
                    project,
                    f"/git/repositories/{repository_id}/pullRequests/{pr_number}/threads",
                ),
                headers=self._auth_headers(),
                json=payload,
            )
            response.raise_for_status()

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

    async def post_inline_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        comments: list[InlineComment],
        body: str = "",
        diff: str | None = None,
    ) -> InlineCommentsResult:
        del repo_full_name, pr_number, commit_id, body, diff
        if comments:
            logger.warning(
                "Azure DevOps inline comments are not supported in MVP; "
                "skipping %d comment(s)",
                len(comments),
            )
        return InlineCommentsResult(posted=(), skipped=tuple(comments))
