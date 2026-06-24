import asyncio
import logging
from typing import Literal

import asyncpg
import typer

from app.cli.review import app as review_app
from app.config import AgentSettings, get_agent_settings, get_settings
from app.mcp.server import create_mcp_server
from app.toolbase.context import ToolContext, build_tool_context

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="coreview-agent",
    help="Nexo Co-Review agent — MCP Git/CI tools and OpenCode runtime.",
    no_args_is_help=True,
)

app.add_typer(review_app, name="review")


async def _resolve_tool_context() -> ToolContext:
    infra = get_agent_settings()
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
        None, help="HTTP host for SSE transport (default from config)."
    ),
    port: int | None = typer.Option(
        None, help="HTTP port for SSE transport (default from config)."
    ),
) -> None:
    """Start the Nexo Co-Review MCP server (coreview Git/CI tools)."""

    async def _run() -> None:
        ctx = await _resolve_tool_context()
        if port is not None:
            infra = AgentSettings(**{**ctx.infra.model_dump(), "mcp_server_port": port})
            ctx = ToolContext(infra=infra, pool=ctx.pool, providers=ctx.providers)
        mcp = create_mcp_server(ctx)
        bind_host = host if host is not None else ctx.infra.mcp_bind_host
        bind_port = port if port is not None else ctx.infra.mcp_server_port
        mcp.settings.host = bind_host
        mcp.settings.port = bind_port

        logger.info("Starting MCP server transport=%s", transport)
        try:
            if transport == "stdio":
                await mcp.run_stdio_async()
            else:
                await mcp.run_sse_async()
        finally:
            if ctx.pool is not None:
                await ctx.pool.close()

    asyncio.run(_run())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
