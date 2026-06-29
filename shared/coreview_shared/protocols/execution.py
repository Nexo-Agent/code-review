"""Execution backend protocols."""

from typing import Protocol

from coreview_shared.protocols.common import (
    CommandRunner,
    Workspace,
    WorkspaceSpec,
)
from coreview_shared.schemas.execution_contracts import (
    ExecutionSubmissionResult,
    ReviewExecutionRequest,
)


class WorkspaceProvider(Protocol):
    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace: ...

    async def cleanup_workspace(self, workspace: Workspace) -> None: ...

    def command_runner(self) -> CommandRunner: ...


class ExecutionBackend(Protocol):
    async def submit_execution(
        self, request: ReviewExecutionRequest
    ) -> ExecutionSubmissionResult: ...
