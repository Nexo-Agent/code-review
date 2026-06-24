from dataclasses import dataclass, field
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


class GitProvider(Protocol):
    def verify_webhook_signature(
        self, payload: bytes, signature: str | None, secret: str
    ) -> bool: ...

    async def fetch_pr_context(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> PRContext: ...

    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> None: ...


class CIProvider(Protocol):
    async def get_ci_summary(
        self, repo_full_name: str, head_sha: str
    ) -> str: ...


class RuntimeProvider(Protocol):
    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace: ...

    async def cleanup_workspace(self, workspace: Workspace) -> None: ...


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
    runtime: RuntimeProvider
    llm: LLMProvider
    extra: dict[str, object] = field(default_factory=dict)
