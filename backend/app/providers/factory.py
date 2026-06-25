from functools import lru_cache

from coreview_shared.protocols import ProviderBundle, RuntimeProvider
from coreview_shared.providers.ci.github import GitHubCIProvider
from coreview_shared.providers.git.github import GitHubProvider
from coreview_shared.runtime.docker.provider import DockerRuntimeProvider
from coreview_shared.runtime.k8s.provider import K8sRuntimeProvider

from app.config import (
    CodeReviewSettings,
    ReviewRuntimeConfig,
    Settings,
    get_code_review_settings,
    get_settings,
)

_GIT_PROVIDERS: dict[str, type[GitHubProvider]] = {
    "github": GitHubProvider,
}

_RUNTIME_PROVIDERS: dict[str, type] = {
    "docker": DockerRuntimeProvider,
    "k8s": K8sRuntimeProvider,
}


def _build_runtime(
    cfg: CodeReviewSettings,
    database_url: str,
) -> DockerRuntimeProvider | K8sRuntimeProvider:
    runtime_cls = _RUNTIME_PROVIDERS.get(cfg.runtime_provider)
    if runtime_cls is None:
        msg = f"Unsupported runtime provider: {cfg.runtime_provider}"
        raise NotImplementedError(msg)

    git_image = cfg.git_image or cfg.workspace_image or "alpine/git:latest"

    if runtime_cls is DockerRuntimeProvider:
        return DockerRuntimeProvider(
            workspace_root=cfg.workspace_root,
            docker_host=cfg.docker_host or None,
            git_image=git_image,
            agent_image=cfg.agent_image,
            agent_network=(cfg.agent_network or "").strip() or None,
            database_url=database_url,
        )

    return K8sRuntimeProvider(
        workspace_root=cfg.workspace_root,
        agent_image=cfg.agent_image,
        database_url=database_url,
        k8s_namespace=cfg.k8s_namespace,
        k8s_agent_config_configmap=cfg.k8s_agent_config_configmap,
    )


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

    git_cls = _GIT_PROVIDERS.get(runtime.git_provider)
    if git_cls is None:
        msg = f"Unsupported git provider: {runtime.git_provider}"
        raise NotImplementedError(msg)

    git = git_cls(token=runtime.github_token)
    ci = GitHubCIProvider(token=runtime.github_token)
    runtime_provider = _build_runtime(cfg, db_settings.database_url)
    return ProviderBundle(git=git, ci=ci, runtime=runtime_provider)


@lru_cache
def get_runtime_provider() -> RuntimeProvider:
    return build_runtime_provider()
