"""Composite runtime provider delegating workspace and execution concerns."""

from __future__ import annotations

from coreview_shared.runtime.protocol import ExecutionBackend, WorkspaceProvider
from coreview_shared.runtime.specs import ReviewJobRequest
from coreview_shared.schemas.execution_contracts import ReviewExecutionRequest
from coreview_shared.workspace.models import Workspace, WorkspaceSpec
from coreview_shared.workspace.protocol import CommandRunner


class CompositeRuntimeProvider:
    """Backward-compatible RuntimeProvider built from split interfaces."""

    def __init__(
        self,
        workspace: WorkspaceProvider,
        execution: ExecutionBackend,
    ) -> None:
        self._workspace = workspace
        self._execution = execution

    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace:
        return await self._workspace.prepare_workspace(spec)

    async def cleanup_workspace(self, workspace: Workspace) -> None:
        await self._workspace.cleanup_workspace(workspace)

    def command_runner(self) -> CommandRunner:
        return self._workspace.command_runner()

    async def run_review_job(self, request: ReviewJobRequest) -> None:
        msg = (
            "run_review_job requires ReviewExecutionRequest; "
            "use submit_execution via review_runner instead"
        )
        raise NotImplementedError(msg)

    async def submit_execution(self, request: ReviewExecutionRequest):
        return await self._execution.submit_execution(request)
