from app.config import AgentSettings
from app.mcp.server import create_mcp_server
from app.toolbase.context import build_tool_context


def test_mcp_server_registers_tools() -> None:
    ctx = build_tool_context(AgentSettings(github_token=""))
    mcp = create_mcp_server(ctx)
    tools = mcp._tool_manager.list_tools()
    names = {tool.name for tool in tools}
    assert "coreview-git_fetch_pr_context" in names
    assert "coreview-ci_get_summary" in names
