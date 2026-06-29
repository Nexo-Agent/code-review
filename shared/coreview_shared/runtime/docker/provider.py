import asyncio
import logging
from pathlib import Path

from coreview_shared.protocols import CommandRunner, Workspace, WorkspaceSpec
from coreview_shared.runtime.docker.client import get_docker_client
from coreview_shared.runtime.docker.command_runner import DockerCommandRunner
from coreview_shared.runtime.docker.job_executor import DockerJobExecutor
from coreview_shared.runtime.specs import ReviewJobRequest

logger = logging.getLogger(__name__)


class DockerRuntimeProvider:
    def __init__(
        self,
        *,
        workspace_root: str,
        docker_host: str | None = None,
        git_image: str = "alpine/git:latest",
        agent_image: str = "cogito-review-agent:dev",
        agent_network: str | None = None,
        database_url: str = "",
        agent_mem_limit: str = "",
        agent_cpus: float = 0.0,
    ) -> None:
        self._workspace_root = Path(workspace_root)
        self._docker_host = docker_host
        self._git_image = git_image
        self._agent_image = agent_image
        self._agent_network = agent_network
        self._database_url = database_url
        self._agent_mem_limit = agent_mem_limit
        self._agent_cpus = agent_cpus
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
        from coreview_shared.runtime.execution.docker_backend import (
            DockerExecutionBackend,
        )
        from coreview_shared.schemas.execution_contracts import (
            CallbackConfig,
            CredentialRefs,
            ExecutionConfig,
            ReviewContext,
            ReviewExecutionRequest,
            RuntimeMetadata,
            SecretRef,
        )

        env = request.environment
        backend = DockerExecutionBackend(self)
        exec_request = ReviewExecutionRequest(
            review_id=request.review_id,
            review=ReviewContext(
                repo_full_name=env.get("COGITO_REVIEW_REPO_FULL_NAME", ""),
                pr_number=int(env.get("COGITO_REVIEW_PR_NUMBER", "0")),
                head_sha=env.get("COGITO_REVIEW_HEAD_SHA", ""),
                git_provider=env.get("COGITO_REVIEW_GIT_PROVIDER", "github"),
            ),
            callback=CallbackConfig(
                url=env.get("COGITO_REVIEW_CALLBACK_URL", ""),
                secret_ref=SecretRef(name="inline", key="secret"),
            ),
            config=ExecutionConfig(
                workspace_root=env.get("COGITO_REVIEW_WORKSPACE_ROOT", "/workspaces"),
                opencode_agent=env.get("COGITO_REVIEW_OPENCODE_AGENT", "code-reviewer"),
                opencode_log_level=env.get("COGITO_REVIEW_OPENCODE_LOG_LEVEL", "INFO"),
                review_timeout_seconds=int(
                    env.get("COGITO_REVIEW_REVIEW_TIMEOUT_SECONDS", "600")
                ),
                system_prompt=env.get("COGITO_REVIEW_SYSTEM_PROMPT", ""),
                llm_provider_id=env.get("COGITO_REVIEW_LLM_PROVIDER_ID", ""),
                llm_base_url=env.get("COGITO_REVIEW_LLM_BASE_URL", ""),
                llm_model=env.get("COGITO_REVIEW_LLM_MODEL", ""),
                opencode_model=env.get("COGITO_REVIEW_OPENCODE_MODEL", ""),
            ),
            credentials=CredentialRefs(
                git_credential_ref=SecretRef(name="inline", key="git"),
                llm_credential_ref=SecretRef(name="inline", key="llm"),
            ),
            runtime_metadata=RuntimeMetadata(),
            resolved_secret_env=_secret_env_from_agent_environment(env),
        )
        result = await backend.submit_execution(exec_request)
        if not result.accepted:
            raise RuntimeError("Docker execution submission was not accepted")

    def _prepare_workspace_sync(self, spec: WorkspaceSpec) -> Workspace:
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        return Workspace(path=self._workspace_root, spec=spec)

    def _cleanup_sync(self, path: Path) -> None:
        # Mirrors persist; agent removes per-review worktrees after each run.
        del path


_SECRET_ENV_KEYS = {
    "COGITO_REVIEW_GITHUB_TOKEN",
    "COGITO_REVIEW_GITLAB_TOKEN",
    "COGITO_REVIEW_GITLAB_BASE_URL",
    "COGITO_REVIEW_BITBUCKET_TOKEN",
    "COGITO_REVIEW_BITBUCKET_DC_TOKEN",
    "COGITO_REVIEW_BITBUCKET_DC_BASE_URL",
    "COGITO_REVIEW_ADO_PAT",
    "COGITO_REVIEW_ADO_ORGANIZATION",
    "COGITO_REVIEW_ADO_PROJECT",
    "COGITO_REVIEW_LLM_API_TOKEN",
    "COGITO_REVIEW_CALLBACK_SECRET",
}


def _secret_env_from_agent_environment(env: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in env.items() if k in _SECRET_ENV_KEYS and v}
