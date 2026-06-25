from typing import Protocol

from coreview_shared.protocols.common import (
    CommandRunner,
    PRContext,
    ReviewFinding,
    Workspace,
    WorkspaceSpec,
)
from coreview_shared.runtime.specs import ReviewJobRequest


class RuntimeProvider(Protocol):
    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace: ...

    async def cleanup_workspace(self, workspace: Workspace) -> None: ...

    def command_runner(self) -> CommandRunner: ...

    async def run_review_job(self, request: ReviewJobRequest) -> None: ...


class LLMProvider(Protocol):
    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> list[ReviewFinding]: ...
