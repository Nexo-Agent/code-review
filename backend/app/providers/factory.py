from functools import lru_cache

from app.config import CodeReviewSettings, get_code_review_settings
from app.providers.ci.github import GitHubCIProvider
from app.providers.git.github import GitHubProvider
from app.providers.llm.opencode import OpenCodeLLMProvider
from app.providers.protocols import ProviderBundle
from app.providers.runtime.docker import DockerRuntimeProvider


def build_providers(settings: CodeReviewSettings | None = None) -> ProviderBundle:
    cfg = settings or get_code_review_settings()

    if cfg.git_provider != "github":
        msg = f"Unsupported git provider: {cfg.git_provider}"
        raise NotImplementedError(msg)

    if cfg.runtime_provider != "docker":
        msg = f"Unsupported runtime provider: {cfg.runtime_provider}"
        raise NotImplementedError(msg)

    git = GitHubProvider(token=cfg.github_token)
    ci = GitHubCIProvider(token=cfg.github_token)
    runtime = DockerRuntimeProvider(
        workspace_root=cfg.workspace_root,
        github_token=cfg.github_token,
        workspace_image=cfg.workspace_image or None,
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
