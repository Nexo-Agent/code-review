import logging
from datetime import UTC, datetime

from coreview_shared.runtime.docker.client import get_docker_client
from coreview_shared.runtime.docker.job_executor import DockerJobExecutor
from coreview_shared.runtime.execution.translate import _non_secret_environment
from coreview_shared.runtime.review_job import build_docker_review_job_spec
from coreview_shared.schemas.execution_contracts import (
    ExecutionSubmissionResult,
    ReviewExecutionRequest,
)

logger = logging.getLogger(__name__)


class DockerRuntimeProvider:
    def __init__(
        self,
        *,
        workspace_root: str,
        docker_host: str | None = None,
        agent_image: str = "cogito-review-agent:dev",
        agent_network: str | None = None,
        database_url: str = "",
        agent_mem_limit: str = "",
        agent_cpus: float = 0.0,
    ) -> None:
        self._workspace_root = workspace_root
        self._docker_host = docker_host
        self._agent_image = agent_image
        self._agent_network = agent_network
        self._database_url = database_url
        self._agent_mem_limit = agent_mem_limit
        self._agent_cpus = agent_cpus
        self._job_executor: DockerJobExecutor | None = None

    def _client(self):
        return get_docker_client(self._docker_host)

    def _get_job_executor(self) -> DockerJobExecutor:
        if self._job_executor is None:
            self._job_executor = DockerJobExecutor(self._client())
        return self._job_executor

    async def submit_execution(
        self, request: ReviewExecutionRequest
    ) -> ExecutionSubmissionResult:
        environment = dict(_non_secret_environment(request))
        environment.update(_resolved_secret_env(request))
        spec = build_docker_review_job_spec(
            review_id=request.review_id,
            agent_image=self._agent_image,
            environment=environment,
            agent_network=self._agent_network,
            agent_mem_limit=self._agent_mem_limit,
            agent_cpus=self._agent_cpus,
            workspace_mount_path=str(self._workspace_root),
        )
        executor = self._get_job_executor()
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
