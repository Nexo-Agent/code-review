import asyncio
import logging
import shutil
from pathlib import Path

from coreview_shared.protocols import CommandRunner, Workspace, WorkspaceSpec
from coreview_shared.runtime.k8s.job_executor import K8sJobExecutor
from coreview_shared.runtime.specs import ReviewJobRequest

logger = logging.getLogger(__name__)


class K8sRuntimeProvider:
    def __init__(
        self,
        *,
        workspace_root: str,
        agent_image: str = "code-review-agent:dev",
        database_url: str = "",
        k8s_namespace: str = "coreview",
        k8s_agent_config_configmap: str = "opencode-config",
    ) -> None:
        self._workspace_root = Path(workspace_root)
        self._agent_image = agent_image
        self._database_url = database_url
        self._k8s_namespace = k8s_namespace
        self._k8s_agent_config_configmap = k8s_agent_config_configmap
        self._job_executor = K8sJobExecutor()

    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace:
        return await asyncio.to_thread(self._prepare_workspace_sync, spec)

    async def cleanup_workspace(self, workspace: Workspace) -> None:
        await asyncio.to_thread(self._cleanup_sync, workspace.path)

    def command_runner(self) -> CommandRunner:
        msg = "K8s runtime command_runner not implemented yet"
        raise NotImplementedError(msg)

    async def run_review_job(self, request: ReviewJobRequest) -> None:
        raise NotImplementedError("K8s runtime not implemented yet")

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
