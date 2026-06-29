"""Docker execution backend — runs agent container immediately."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from coreview_shared.runtime.docker.provider import DockerRuntimeProvider
from coreview_shared.runtime.execution.translate import _non_secret_environment
from coreview_shared.runtime.review_job import build_docker_review_job_spec
from coreview_shared.schemas.execution_contracts import (
    ExecutionSubmissionResult,
    ReviewExecutionRequest,
)

logger = logging.getLogger(__name__)


class DockerExecutionBackend:
    """Submit execution by running a one-shot Docker agent container."""

    def __init__(self, provider: DockerRuntimeProvider) -> None:
        self._provider = provider

    async def submit_execution(
        self, request: ReviewExecutionRequest
    ) -> ExecutionSubmissionResult:
        environment = dict(_non_secret_environment(request))
        environment.update(_resolved_secret_env(request))
        spec = build_docker_review_job_spec(
            review_id=request.review_id,
            agent_image=self._provider._agent_image,
            environment=environment,
            agent_network=self._provider._agent_network,
            agent_mem_limit=self._provider._agent_mem_limit,
            agent_cpus=self._provider._agent_cpus,
            workspace_mount_path=str(self._provider._workspace_root),
        )
        executor = self._provider._get_job_executor()
        await executor.cleanup_stale(spec.labels)
        result = await executor.run(spec)
        if result.exit_code != 0:
            msg = f"Review agent container failed (exit {result.exit_code})"
            if result.log_tail:
                msg = f"{msg}: {result.log_tail}"
            raise RuntimeError(msg)
        logger.info(
            "Review agent container for %s exited successfully",
            request.review_id,
        )
        return ExecutionSubmissionResult(
            backend_kind="docker",
            accepted=True,
            submitted_at=datetime.now(UTC),
            external_ref=spec.job_id,
            waits_for_completion=True,
        )


def _resolved_secret_env(request: ReviewExecutionRequest) -> dict[str, str]:
    return dict(request.resolved_secret_env)
