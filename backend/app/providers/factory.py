from functools import lru_cache

from coreview_shared.ci.bitbucket_cloud import BitbucketCloudCIProvider
from coreview_shared.ci.bitbucket_dc import BitbucketDataCenterCIProvider
from coreview_shared.ci.github import GitHubCIProvider
from coreview_shared.ci.gitlab import GitLabCIProvider
from coreview_shared.ci.noop import NoOpCIProvider
from coreview_shared.git.azure_devops import AzureDevOpsProvider
from coreview_shared.git.bitbucket_cloud import BitbucketCloudProvider
from coreview_shared.git.bitbucket_dc import BitbucketDataCenterProvider
from coreview_shared.git.github import GitHubProvider
from coreview_shared.git.gitlab import GitLabProvider
from coreview_shared.protocols import ProviderBundle, RuntimeProvider
from coreview_shared.runtime.composite import CompositeRuntimeProvider
from coreview_shared.runtime.docker.provider import DockerRuntimeProvider
from coreview_shared.runtime.execution.docker_backend import DockerExecutionBackend
from coreview_shared.runtime.execution.k8s_backend import KubernetesExecutionBackend
from coreview_shared.runtime.k8s.provider import K8sRuntimeProvider

from app.config import (
    CodeReviewSettings,
    ReviewRuntimeConfig,
    Settings,
    get_code_review_settings,
    get_settings,
)

_GIT_PROVIDERS: dict[str, type] = {
    "github": GitHubProvider,
    "azure-devops": AzureDevOpsProvider,
    "gitlab": GitLabProvider,
    "bitbucket": BitbucketCloudProvider,
    "bitbucket-dc": BitbucketDataCenterProvider,
}

_RUNTIME_PROVIDERS: dict[str, type] = {
    "docker": DockerRuntimeProvider,
    "k8s": K8sRuntimeProvider,
}


def _build_git_provider(runtime: ReviewRuntimeConfig):
    git_cls = _GIT_PROVIDERS.get(runtime.git_provider)
    if git_cls is None:
        msg = f"Unsupported git provider: {runtime.git_provider}"
        raise NotImplementedError(msg)

    if git_cls is GitHubProvider:
        return GitHubProvider(token=runtime.github_token)
    if git_cls is GitLabProvider:
        return GitLabProvider(
            token=runtime.gitlab_token,
            base_url=runtime.gitlab_base_url,
        )
    if git_cls is BitbucketCloudProvider:
        return BitbucketCloudProvider(token=runtime.bitbucket_token)
    if git_cls is BitbucketDataCenterProvider:
        return BitbucketDataCenterProvider(
            token=runtime.bitbucket_dc_token,
            base_url=runtime.bitbucket_dc_base_url,
        )
    return AzureDevOpsProvider(
        pat=runtime.ado_pat,
        organization=runtime.ado_organization,
        project=runtime.ado_project,
    )


def _build_ci_provider(runtime: ReviewRuntimeConfig):
    if runtime.git_provider == "github":
        return GitHubCIProvider(token=runtime.github_token)
    if runtime.git_provider == "gitlab":
        return GitLabCIProvider(
            token=runtime.gitlab_token,
            base_url=runtime.gitlab_base_url,
        )
    if runtime.git_provider == "bitbucket":
        return BitbucketCloudCIProvider(token=runtime.bitbucket_token)
    if runtime.git_provider == "bitbucket-dc":
        return BitbucketDataCenterCIProvider(
            token=runtime.bitbucket_dc_token,
            base_url=runtime.bitbucket_dc_base_url,
        )
    return NoOpCIProvider()


def _build_runtime(
    cfg: CodeReviewSettings,
    database_url: str,
) -> CompositeRuntimeProvider:
    runtime_cls = _RUNTIME_PROVIDERS.get(cfg.runtime_provider)
    if runtime_cls is None:
        msg = f"Unsupported runtime provider: {cfg.runtime_provider}"
        raise NotImplementedError(msg)

    git_image = cfg.git_image or cfg.workspace_image or "alpine/git:latest"

    if runtime_cls is DockerRuntimeProvider:
        workspace = DockerRuntimeProvider(
            workspace_root=cfg.workspace_root,
            docker_host=cfg.docker_host or None,
            git_image=git_image,
            agent_image=cfg.agent_image,
            agent_network=(cfg.agent_network or "").strip() or None,
            database_url=database_url,
            agent_mem_limit=cfg.agent_mem_limit,
            agent_cpus=cfg.agent_cpus,
        )
        execution = DockerExecutionBackend(workspace)
        return CompositeRuntimeProvider(workspace=workspace, execution=execution)

    workspace = K8sRuntimeProvider(
        workspace_root=cfg.workspace_root,
        agent_image=cfg.agent_image,
        database_url=database_url,
        k8s_namespace=cfg.k8s_run_namespace or cfg.k8s_namespace,
        k8s_agent_config_configmap=cfg.k8s_agent_config_configmap,
    )
    execution = KubernetesExecutionBackend(
        namespace=cfg.k8s_run_namespace or cfg.k8s_namespace,
        agent_image=cfg.agent_image,
        kubeconfig_path=cfg.k8s_kubeconfig_path,
    )
    return CompositeRuntimeProvider(workspace=workspace, execution=execution)


def build_execution_backend(
    infra: CodeReviewSettings | None = None,
    *,
    app_settings: Settings | None = None,
):
    runtime = build_runtime_provider(infra=infra, app_settings=app_settings)
    return runtime._execution


def build_runtime_provider(
    infra: CodeReviewSettings | None = None,
    *,
    app_settings: Settings | None = None,
) -> RuntimeProvider:
    cfg = infra or get_code_review_settings()
    db_settings = app_settings or get_settings()
    return _build_runtime(cfg, db_settings.database_url)


def build_providers(
    runtime: ReviewRuntimeConfig,
    *,
    infra: CodeReviewSettings | None = None,
    app_settings: Settings | None = None,
) -> ProviderBundle:
    cfg = infra or get_code_review_settings()
    db_settings = app_settings or get_settings()

    git = _build_git_provider(runtime)
    ci = _build_ci_provider(runtime)
    runtime_provider = _build_runtime(cfg, db_settings.database_url)
    return ProviderBundle(git=git, ci=ci, runtime=runtime_provider)


@lru_cache
def get_runtime_provider() -> RuntimeProvider:
    return build_runtime_provider()
