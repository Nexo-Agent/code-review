from unittest.mock import AsyncMock

import pytest
from coreview_shared.protocols import PRContext, PRMetadata, ProviderBundle

from app.config import AgentSettings
from app.toolbase import ci_tools, git_tools
from app.toolbase.context import ToolContext


@pytest.fixture
def tool_context() -> ToolContext:
    git = AsyncMock()
    ci = AsyncMock()
    providers = ProviderBundle(git=git, ci=ci)
    return ToolContext(infra=AgentSettings(), providers=providers)


@pytest.mark.asyncio
async def test_git_tools_fetch_pr_context(tool_context: ToolContext) -> None:
    tool_context.providers.git.fetch_pr_context.return_value = PRContext(
        metadata=PRMetadata(
            repo_full_name="org/repo",
            pr_number=1,
            title="T",
            author="a",
            head_sha="h",
            base_sha="b",
            head_ref="hr",
            base_ref="br",
            html_url="url",
        ),
        diff="diff",
        ci_summary="",
    )
    result = await git_tools.fetch_pr_context(tool_context, "org/repo", 1, "h")
    assert result["metadata"]["title"] == "T"
    assert result["diff"] == "diff"


@pytest.mark.asyncio
async def test_ci_tools_get_summary(tool_context: ToolContext) -> None:
    tool_context.providers.ci.get_ci_summary.return_value = "CI ok"
    result = await ci_tools.get_ci_summary(tool_context, "org/repo", "sha")
    assert result["summary"] == "CI ok"
