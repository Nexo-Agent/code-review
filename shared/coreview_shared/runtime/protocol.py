from typing import Protocol

from coreview_shared.runtime.specs import ReviewJobRequest
from coreview_shared.schemas.execution_contracts import (
    ExecutionSubmissionResult,
    ReviewExecutionRequest,
)
from coreview_shared.workspace.models import Workspace, WorkspaceSpec
from coreview_shared.workspace.protocol import CommandRunner


class RuntimeProvider(Protocol):
    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace: ...

    async def cleanup_workspace(self, workspace: Workspace) -> None: ...

    def command_runner(self) -> CommandRunner: ...

    async def run_review_job(self, request: ReviewJobRequest) -> None: ...


class WorkspaceProvider(Protocol):
    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace: ...

    async def cleanup_workspace(self, workspace: Workspace) -> None: ...

    def command_runner(self) -> CommandRunner: ...


class ExecutionBackend(Protocol):
    async def submit_execution(
        self, request: ReviewExecutionRequest
    ) -> ExecutionSubmissionResult: ...
