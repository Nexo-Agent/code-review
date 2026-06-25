"""OpenCode configuration builders shared by backend and agent."""

from __future__ import annotations

from typing import Any


def build_mcp_config() -> dict[str, Any]:
    """Configure coreview MCP as a local stdio subprocess for `opencode run`."""
    return {
        "coreview": {
            "type": "local",
            "command": ["coreview-agent", "serve", "--transport", "stdio"],
            "enabled": True,
        }
    }


def build_code_reviewer_agent_config(agent_name: str) -> dict[str, Any]:
    return {
        "description": "Reviews PR for bugs, security, and maintainability",
        "mode": "subagent",
        "tools": {
            "coreview-git_fetch_pr_context": True,
            "coreview-ci_get_summary": True,
        },
        "permission": {
            "edit": "deny",
            "write": "deny",
            "bash": {"*": "deny"},
        },
        "prompt": (
            "You are a code reviewer. Use MCP tools to gather context "
            "before reviewing: call coreview-git_fetch_pr_context and "
            "coreview-ci_get_summary with the repository and PR details "
            "from the prompt. Analyze the cloned workspace at the session "
            "directory. Do not post GitHub comments via MCP. Return findings "
            "as JSON matching the outputFormat schema in your final response. "
            "Focus on bugs, security issues, performance problems, and "
            "missing tests."
        ),
    }


def llm_provider_block(
    provider_id: str,
    model_id: str,
    *,
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    return {
        provider_id: {
            "npm": "@ai-sdk/openai-compatible",
            "name": "OpenAI Compatible API",
            "options": {
                "baseURL": base_url,
                "apiKey": api_key,
            },
            "models": {
                model_id: {
                    "name": model_id,
                }
            },
        }
    }
