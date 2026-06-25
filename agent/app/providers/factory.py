from coreview_shared.protocols import ProviderBundle
from coreview_shared.providers.ci.github import GitHubCIProvider
from coreview_shared.providers.ci.noop import NoOpCIProvider
from coreview_shared.providers.git.azure_devops import AzureDevOpsProvider
from coreview_shared.providers.git.github import GitHubProvider

from app.config import AgentSettings, get_agent_settings

_GIT_PROVIDERS: dict[str, type] = {
    "github": GitHubProvider,
    "azure-devops": AzureDevOpsProvider,
}


def build_providers(
    *,
    github_token: str = "",
    git_provider: str = "github",
    ado_pat: str = "",
    ado_organization: str = "",
    ado_project: str = "",
) -> ProviderBundle:
    git_cls = _GIT_PROVIDERS.get(git_provider)
    if git_cls is None:
        msg = f"Unsupported git provider: {git_provider}"
        raise NotImplementedError(msg)

    if git_cls is GitHubProvider:
        git = GitHubProvider(token=github_token)
        ci = GitHubCIProvider(token=github_token)
    else:
        git = AzureDevOpsProvider(
            pat=ado_pat,
            organization=ado_organization,
            project=ado_project,
        )
        ci = NoOpCIProvider()
    return ProviderBundle(git=git, ci=ci)


def build_providers_from_env(
    settings: AgentSettings | None = None,
) -> ProviderBundle:
    cfg = settings or get_agent_settings()
    return build_providers(
        github_token=cfg.github_token,
        git_provider=cfg.git_provider,
        ado_pat=cfg.ado_pat,
        ado_organization=cfg.ado_organization,
        ado_project=cfg.ado_project,
    )
