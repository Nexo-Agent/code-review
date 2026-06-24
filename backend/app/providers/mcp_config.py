"""MCP configuration helpers for OpenCode."""

from app.config import CodeReviewSettings


def build_mcp_config(infra: CodeReviewSettings) -> dict:
    return {
        "coreview": {
            "type": "remote",
            "url": infra.mcp_server_url,
            "enabled": True,
        }
    }


def build_code_reviewer_agent_config(agent_name: str) -> dict:
    return {
        "description": "Reviews PR for bugs, security, and maintainability",
        "mode": "subagent",
        "tools": {
            "coreview-git_*": True,
            "coreview-ci_*": True,
        },
        "permission": {
            "edit": "deny",
            "write": "deny",
            "bash": {"*": "deny"},
        },
        "prompt": (
            "You are a code reviewer. Use MCP tools to gather context "
            "before reviewing: call coreview-git_fetch_pr_context and "
            "coreview-ci_get_ci_summary with the repository and PR details "
            "from the prompt. Analyze the cloned workspace at the session "
            "directory. Return findings as JSON matching the outputFormat "
            "schema. For line-specific issues, use "
            "coreview-git_post_inline_comments. "
            "Focus on bugs, security issues, performance problems, and "
            "missing tests."
        ),
    }


def default_opencode_config_path():
    from pathlib import Path

    return Path("opencode.json")
