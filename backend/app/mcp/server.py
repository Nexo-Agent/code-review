"""Nexo Co-Review MCP server (nexo-coreview) exposing Git and CI tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.toolbase import ci_tools, git_tools
from app.toolbase.context import ToolContext

logger = logging.getLogger(__name__)


def create_mcp_server(ctx: ToolContext) -> FastMCP:
    mcp = FastMCP(
        name="coreview",
        instructions="Git and CI tools for code review workflows.",
        host="0.0.0.0",
        port=ctx.infra.mcp_server_port,
        transport_security=None,
    )

    @mcp.tool(name="coreview-git_fetch_pr_context")
    async def git_fetch_pr_context(
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
    ) -> dict[str, Any]:
        """Fetch pull request metadata and diff."""
        return await git_tools.fetch_pr_context(
            ctx, repo_full_name, pr_number, head_sha
        )

    @mcp.tool(name="coreview-git_get_pr_metadata")
    async def git_get_pr_metadata(
        repo_full_name: str,
        pr_number: int,
    ) -> dict[str, Any]:
        """Fetch pull request metadata."""
        return await git_tools.get_pr_metadata(ctx, repo_full_name, pr_number)

    @mcp.tool(name="coreview-git_get_pr_diff")
    async def git_get_pr_diff(
        repo_full_name: str,
        pr_number: int,
    ) -> dict[str, str]:
        """Fetch pull request diff."""
        return await git_tools.get_pr_diff(ctx, repo_full_name, pr_number)

    @mcp.tool(name="coreview-git_post_review_comment")
    async def git_post_review_comment(
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> dict[str, str]:
        """Post a summary comment on the pull request."""
        return await git_tools.post_review_comment(
            ctx, repo_full_name, pr_number, body
        )

    @mcp.tool(name="coreview-git_post_inline_comments")
    async def git_post_inline_comments(
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        comments: list[dict[str, Any]],
        body: str = "",
    ) -> dict[str, str]:
        """Post inline review comments on specific lines."""
        return await git_tools.post_inline_comments(
            ctx,
            repo_full_name,
            pr_number,
            commit_id,
            comments,
            body=body,
        )

    @mcp.tool(name="coreview-ci_get_summary")
    async def ci_get_summary(
        repo_full_name: str,
        head_sha: str,
    ) -> dict[str, str]:
        """Fetch CI status summary for a commit."""
        return await ci_tools.get_ci_summary(ctx, repo_full_name, head_sha)

    return mcp
