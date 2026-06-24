from app.config import AgentSettings, get_agent_settings
from app.providers.ci.github import GitHubCIProvider
from app.providers.git.github import GitHubProvider
from app.providers.protocols import ProviderBundle
from app.repositories.repo_integrations import RepoIntegrationRow

_GIT_PROVIDERS: dict[str, type[GitHubProvider]] = {
    "github": GitHubProvider,
}


def build_providers(
    *,
    github_token: str,
    git_provider: str = "github",
) -> ProviderBundle:
    git_cls = _GIT_PROVIDERS.get(git_provider)
    if git_cls is None:
        msg = f"Unsupported git provider: {git_provider}"
        raise NotImplementedError(msg)

    git = git_cls(token=github_token)
    ci = GitHubCIProvider(token=github_token)
    return ProviderBundle(git=git, ci=ci)


def build_providers_from_integration(
    repo_integration: RepoIntegrationRow,
) -> ProviderBundle:
    return build_providers(
        github_token=repo_integration.github_token,
        git_provider=repo_integration.git_provider,
    )


def build_providers_from_env(
    settings: AgentSettings | None = None,
) -> ProviderBundle:
    cfg = settings or get_agent_settings()
    return build_providers(
        github_token=cfg.github_token,
        git_provider=cfg.git_provider,
    )
