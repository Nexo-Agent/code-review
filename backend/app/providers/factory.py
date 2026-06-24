from functools import lru_cache

from app.config import CodeReviewSettings, get_code_review_settings
from app.providers.ci.github import GitHubCIProvider
from app.providers.git.github import GitHubProvider
from app.providers.llm.opencode import OpenCodeLLMProvider
from app.providers.protocols import ProviderBundle
from app.providers.runtime.docker import DockerRuntimeProvider

_GIT_PROVIDERS: dict[str, type[GitHubProvider]] = {
    "github": GitHubProvider,
}

_RUNTIME_PROVIDERS: dict[str, type[DockerRuntimeProvider]] = {
    "docker": DockerRuntimeProvider,
}


def build_providers(settings: CodeReviewSettings | None = None) -> ProviderBundle:
    cfg = settings or get_code_review_settings()

    git_cls = _GIT_PROVIDERS.get(cfg.git_provider)
    if git_cls is None:
        msg = f"Unsupported git provider: {cfg.git_provider}"
        raise NotImplementedError(msg)

    runtime_cls = _RUNTIME_PROVIDERS.get(cfg.runtime_provider)
    if runtime_cls is None:
        msg = f"Unsupported runtime provider: {cfg.runtime_provider}"
        raise NotImplementedError(msg)

    git_image = cfg.git_image or cfg.workspace_image or "alpine/git:latest"

    git = git_cls(token=cfg.github_token)
    ci = GitHubCIProvider(token=cfg.github_token)
    runtime = runtime_cls(
        workspace_root=cfg.workspace_root,
        docker_host=cfg.docker_host or None,
        git_image=git_image,
    )
    llm = OpenCodeLLMProvider(
        server_url=cfg.opencode_server_url,
        username=cfg.opencode_server_username,
        password=cfg.opencode_server_password,
        agent=cfg.opencode_agent,
        model=cfg.resolved_opencode_model,
        timeout_seconds=cfg.review_timeout_seconds,
    )
    return ProviderBundle(git=git, ci=ci, runtime=runtime, llm=llm)


@lru_cache
def get_providers() -> ProviderBundle:
    return build_providers()
