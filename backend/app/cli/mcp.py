import asyncio
import logging
from typing import Literal

import asyncpg
import typer

from app.config import CodeReviewSettings, get_code_review_settings, get_settings
from app.mcp.server import create_mcp_server
from app.toolbase.context import ToolContext, build_tool_context

logger = logging.getLogger(__name__)

app = typer.Typer(help="MCP server for Git/CI tools.")


async def _resolve_tool_context() -> ToolContext:
    infra = get_code_review_settings()
    settings = get_settings()
    try:
        pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=1,
            max_size=3,
        )
        return build_tool_context(infra, pool=pool)
    except Exception:
        logger.warning(
            "Could not connect to database for MCP; using env-only fallback",
            exc_info=True,
        )
        return build_tool_context(infra)


@app.command("serve")
def serve(
    transport: Literal["stdio", "sse"] = typer.Option(
        "stdio", help="MCP transport (stdio or sse)."
    ),
    host: str | None = typer.Option(
        None, help="HTTP host for SSE transport (default 0.0.0.0)."
    ),
    port: int | None = typer.Option(
        None, help="HTTP port for SSE transport (default from config)."
    ),
) -> None:
    """Start the Nexo Co-Review MCP server (nexo-coreview)."""

    async def _run() -> None:
        ctx = await _resolve_tool_context()
        if port is not None:
            infra = CodeReviewSettings(
                **{**ctx.infra.model_dump(), "mcp_server_port": port}
            )
            ctx = ToolContext(infra=infra, pool=ctx.pool, providers=ctx.providers)

        mcp = create_mcp_server(ctx)
        if host is not None:
            mcp.settings.host = host
        if port is not None:
            mcp.settings.port = port

        logger.info("Starting MCP server transport=%s", transport)
        mcp.run(transport=transport)

    asyncio.run(_run())
