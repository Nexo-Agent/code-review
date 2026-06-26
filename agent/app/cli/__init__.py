import asyncio
import logging

import typer

from app.cli.review import app as review_app
from app.config import get_agent_settings
from app.mcp.server import create_mcp_server
from app.toolbase.context import ToolContext, build_tool_context

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="cogito-review-agent",
    help="Cogito Review agent — MCP Git/CI tools and OpenCode runtime.",
    no_args_is_help=True,
)

app.add_typer(review_app, name="review")


def _resolve_tool_context() -> ToolContext:
    infra = get_agent_settings()
    return build_tool_context(infra)


@app.command("serve")
def serve() -> None:
    """Start the Cogito Review MCP server over stdio."""

    async def _run() -> None:
        ctx = _resolve_tool_context()
        mcp = create_mcp_server(ctx)
        logger.info("Starting MCP server (stdio)")
        await mcp.run_stdio_async()

    asyncio.run(_run())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
