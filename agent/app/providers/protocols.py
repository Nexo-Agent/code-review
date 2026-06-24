from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PRMetadata:
    repo_full_name: str
    pr_number: int
    title: str
    author: str
    head_sha: str
    base_sha: str
    head_ref: str
    base_ref: str
    html_url: str


@dataclass(frozen=True, slots=True)
class PRContext:
    metadata: PRMetadata
    diff: str
    ci_summary: str = ""


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    severity: str
    title: str
    body: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceSpec:
    review_id: str
    repo_full_name: str
    pr_number: int
    head_sha: str


@dataclass(frozen=True, slots=True)
class Workspace:
    path: Path
    spec: WorkspaceSpec


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    event_type: str
    action: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    delivery_id: str | None


@dataclass(frozen=True, slots=True)
class InlineComment:
    path: str
    line: int
    body: str
    side: str = "RIGHT"


@dataclass(frozen=True, slots=True)
class InlineCommentsResult:
    posted: tuple[InlineComment, ...]
    skipped: tuple[InlineComment, ...]


class CommandRunner(Protocol):
    async def run(self, args: list[str], cwd: Path) -> None: ...


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

    async def clone_repository(
        self,
        spec: WorkspaceSpec,
        workspace: Workspace,
        runner: CommandRunner,
    ) -> None: ...

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


class CIProvider(Protocol):
    async def get_ci_summary(self, repo_full_name: str, head_sha: str) -> str: ...


class RuntimeProvider(Protocol):
    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace: ...

    async def cleanup_workspace(self, workspace: Workspace) -> None: ...

    def command_runner(self) -> CommandRunner: ...


class LLMProvider(Protocol):
    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> list[ReviewFinding]: ...


@dataclass(slots=True)
class ProviderBundle:
    git: GitProvider
    ci: CIProvider
