from typing import Protocol

from coreview_shared.schemas.execution_contracts import (
    ExecutionSubmissionResult,
    ReviewExecutionRequest,
)


class RuntimeProvider(Protocol):
    """Execution backend contract used by the backend worker.

    Runtime providers only submit review execution to a backend. Repository
    workspace preparation, local Git commands, and cleanup are owned by the
    agent runtime once the backend launches it.
    """

    async def submit_execution(
        self, request: ReviewExecutionRequest
    ) -> ExecutionSubmissionResult: ...
