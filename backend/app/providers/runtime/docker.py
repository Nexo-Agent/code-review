import asyncio
import logging
import shutil
from pathlib import Path

from app.providers.protocols import CommandRunner, Workspace, WorkspaceSpec
from app.providers.runtime.command_runner import DockerCommandRunner
from app.providers.runtime.docker_client import get_docker_client

logger = logging.getLogger(__name__)


class DockerRuntimeProvider:
    def __init__(
        self,
        workspace_root: str,
        docker_host: str | None = None,
        git_image: str = "alpine/git:latest",
    ) -> None:
        self._workspace_root = Path(workspace_root)
        self._docker_host = docker_host
        self._git_image = git_image
        self._runner: DockerCommandRunner | None = None

    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace:
        return await asyncio.to_thread(self._prepare_workspace_sync, spec)

    async def cleanup_workspace(self, workspace: Workspace) -> None:
        await asyncio.to_thread(self._cleanup_sync, workspace.path)

    def command_runner(self) -> CommandRunner:
        if self._runner is None:
            client = get_docker_client(self._docker_host)
            self._runner = DockerCommandRunner(
                client=client,
                git_image=self._git_image,
                workspace_root=self._workspace_root,
            )
        return self._runner

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
