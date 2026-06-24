from dataclasses import dataclass

from app.config import AgentSettings, get_agent_settings
from app.providers.factory import build_providers_from_env
from app.providers.protocols import ProviderBundle


@dataclass(slots=True)
class ToolContext:
    infra: AgentSettings
    providers: ProviderBundle | None = None


def build_tool_context(
    settings: AgentSettings | None = None,
    *,
    providers: ProviderBundle | None = None,
) -> ToolContext:
    infra = settings or get_agent_settings()
    if providers is None and infra.github_token:
        providers = build_providers_from_env(infra)
    return ToolContext(infra=infra, providers=providers)


async def providers_for_repo(
    ctx: ToolContext,
    repo_full_name: str,
) -> ProviderBundle:
    del repo_full_name
    if ctx.providers is not None:
        return ctx.providers
    msg = "ToolContext has no providers; inject NEXO_COREVIEW_GITHUB_TOKEN via env"
    raise RuntimeError(msg)
