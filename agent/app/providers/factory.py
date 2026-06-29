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
from coreview_shared.protocols import ProviderBundle

from app.config import AgentSettings, get_agent_settings

_GIT_PROVIDERS: dict[str, type] = {
    "github": GitHubProvider,
    "azure-devops": AzureDevOpsProvider,
    "gitlab": GitLabProvider,
    "bitbucket": BitbucketCloudProvider,
    "bitbucket-dc": BitbucketDataCenterProvider,
}


def build_providers(
    *,
    github_token: str = "",
    git_provider: str = "github",
    ado_pat: str = "",
    ado_organization: str = "",
    ado_project: str = "",
    gitlab_token: str = "",
    gitlab_base_url: str = "",
    bitbucket_token: str = "",
    bitbucket_dc_token: str = "",
    bitbucket_dc_base_url: str = "",
) -> ProviderBundle:
    git_cls = _GIT_PROVIDERS.get(git_provider)
    if git_cls is None:
        msg = f"Unsupported git provider: {git_provider}"
        raise NotImplementedError(msg)

    if git_cls is GitHubProvider:
        git = GitHubProvider(token=github_token)
        ci = GitHubCIProvider(token=github_token)
    elif git_cls is GitLabProvider:
        git = GitLabProvider(token=gitlab_token, base_url=gitlab_base_url)
        ci = GitLabCIProvider(token=gitlab_token, base_url=gitlab_base_url)
    elif git_cls is BitbucketCloudProvider:
        git = BitbucketCloudProvider(token=bitbucket_token)
        ci = BitbucketCloudCIProvider(token=bitbucket_token)
    elif git_cls is BitbucketDataCenterProvider:
        git = BitbucketDataCenterProvider(
            token=bitbucket_dc_token,
            base_url=bitbucket_dc_base_url,
        )
        ci = BitbucketDataCenterCIProvider(
            token=bitbucket_dc_token,
            base_url=bitbucket_dc_base_url,
        )
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
        gitlab_token=cfg.gitlab_token,
        gitlab_base_url=cfg.gitlab_base_url,
        bitbucket_token=cfg.bitbucket_token,
        bitbucket_dc_token=cfg.bitbucket_dc_token,
        bitbucket_dc_base_url=cfg.bitbucket_dc_base_url,
    )
