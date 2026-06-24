"""OpenCode config materialization from injected env vars."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.config import AgentSettings


def _llm_provider_block(settings: AgentSettings) -> dict[str, Any]:
    provider_id = settings.llm_provider_id
    model_id = settings.llm_model
    return {
        provider_id: {
            "npm": "@ai-sdk/openai-compatible",
            "name": "OpenAI Compatible API",
            "options": {
                "baseURL": settings.llm_base_url,
                "apiKey": settings.llm_api_token,
            },
            "models": {
                model_id: {
                    "name": model_id,
                }
            },
        }
    }


def build_mcp_config() -> dict[str, Any]:
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


def build_opencode_config(settings: AgentSettings) -> dict[str, Any]:
    agent_name = settings.opencode_agent
    agent_cfg = build_code_reviewer_agent_config(agent_name)
    agent_cfg["model"] = settings.resolved_opencode_model

    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": build_mcp_config(),
        "tools": {
            "bash": False,
        },
        "provider": _llm_provider_block(settings),
        "agent": {
            agent_name: agent_cfg,
        },
    }


def materialize_opencode_config(
    settings: AgentSettings,
    *,
    review_id: str | None = None,
) -> Path:
    """Write ephemeral OpenCode config from env-injected settings."""
    rid = review_id or settings.review_id or "review"
    path = Path(f"/tmp/opencode-{rid}.json")
    config = build_opencode_config(settings)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.environ["OPENCODE_CONFIG"] = str(path)
    return path
