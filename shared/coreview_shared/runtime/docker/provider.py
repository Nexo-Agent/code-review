import asyncio
import logging
import shutil
from pathlib import Path

from coreview_shared.protocols import CommandRunner, Workspace, WorkspaceSpec
from coreview_shared.runtime.docker.client import get_docker_client
from coreview_shared.runtime.docker.command_runner import DockerCommandRunner
from coreview_shared.runtime.docker.job_executor import DockerJobExecutor
from coreview_shared.runtime.review_job import build_docker_review_job_spec
from coreview_shared.runtime.specs import ReviewJobRequest

logger = logging.getLogger(__name__)


class DockerRuntimeProvider:
    def __init__(
        self,
        *,
        workspace_root: str,
        docker_host: str | None = None,
        git_image: str = "alpine/git:latest",
        agent_image: str = "code-review-agent:dev",
        agent_network: str | None = None,
        database_url: str = "",
    ) -> None:
        self._workspace_root = Path(workspace_root)
        self._docker_host = docker_host
        self._git_image = git_image
        self._agent_image = agent_image
        self._agent_network = agent_network
        self._database_url = database_url
        self._runner: DockerCommandRunner | None = None
        self._job_executor: DockerJobExecutor | None = None

    def _client(self):
        return get_docker_client(self._docker_host)

    def _get_job_executor(self) -> DockerJobExecutor:
        if self._job_executor is None:
            self._job_executor = DockerJobExecutor(self._client())
        return self._job_executor

    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace:
        return await asyncio.to_thread(self._prepare_workspace_sync, spec)

    async def cleanup_workspace(self, workspace: Workspace) -> None:
        await asyncio.to_thread(self._cleanup_sync, workspace.path)

    def command_runner(self) -> CommandRunner:
        if self._runner is None:
            self._runner = DockerCommandRunner(
                client=self._client(),
                git_image=self._git_image,
                workspace_root=self._workspace_root,
            )
        return self._runner

    async def run_review_job(self, request: ReviewJobRequest) -> None:
        spec = build_docker_review_job_spec(
            review_id=request.review_id,
            agent_image=self._agent_image,
            environment=dict(request.environment),
            agent_network=self._agent_network,
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

    def _prepare_workspace_sync(self, spec: WorkspaceSpec) -> Workspace:
        path = self._workspace_root / spec.review_id
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
        return Workspace(path=path, spec=spec)

    def _cleanup_sync(self, path: Path) -> None:
        parent = path.parent if path.name == "repo" else path
        if parent.exists() and parent.is_dir():
            shutil.rmtree(parent, ignore_errors=True)
