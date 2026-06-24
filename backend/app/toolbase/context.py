from dataclasses import dataclass

import asyncpg

from app.config import CodeReviewSettings, get_code_review_settings
from app.providers.protocols import ProviderBundle
from app.services.provider_resolution import build_providers_for_repo


@dataclass(slots=True)
class ToolContext:
    infra: CodeReviewSettings
    pool: asyncpg.Pool | None = None
    providers: ProviderBundle | None = None


def build_tool_context(
    settings: CodeReviewSettings | None = None,
    *,
    pool: asyncpg.Pool | None = None,
    providers: ProviderBundle | None = None,
) -> ToolContext:
    infra = settings or get_code_review_settings()
    return ToolContext(infra=infra, pool=pool, providers=providers)


async def providers_for_repo(
    ctx: ToolContext,
    repo_full_name: str,
) -> ProviderBundle:
    if ctx.pool is not None:
        async with ctx.pool.acquire() as conn:
            return await build_providers_for_repo(conn, repo_full_name, ctx.infra)
    if ctx.providers is not None:
        return ctx.providers
    msg = "ToolContext has no database pool or fallback providers"
    raise RuntimeError(msg)
