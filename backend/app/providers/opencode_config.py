import json
from pathlib import Path
from typing import Any

from coreview_shared.agent.config import (
    build_code_reviewer_agent_config,
    build_headless_opencode_permissions,
    build_headless_opencode_tools,
    build_mcp_config,
    build_review_skills_config,
    llm_provider_block,
)

from app.config import CodeReviewSettings, get_code_review_settings


def merge_llm_provider_blocks(
    providers: list[Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for row in providers:
        block = llm_provider_block(
            row.provider_id,
            row.model,
            base_url=row.base_url,
            api_key=row.api_token,
        )
        provider_key = row.provider_id
        if provider_key not in merged:
            merged.update(block)
            continue
        merged[provider_key]["models"].update(block[provider_key]["models"])
    return merged


def build_opencode_config_from_llm_providers(
    providers: list[Any],
    default: Any | None,
    infra: CodeReviewSettings | None = None,
) -> dict[str, Any]:
    """Build OpenCode config with all registered LLM providers."""
    infra = infra or get_code_review_settings()
    agent_name = infra.opencode_agent
    agent_cfg = build_code_reviewer_agent_config(agent_name)
    if default is not None:
        agent_cfg["model"] = default.resolved_opencode_model

    provider_blocks = merge_llm_provider_blocks(providers) if providers else {}

    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": build_mcp_config(),
        "skills": build_review_skills_config(),
        "tools": build_headless_opencode_tools(),
        "permission": build_headless_opencode_permissions(),
        "provider": provider_blocks,
        "agent": {
            agent_name: agent_cfg,
        },
    }


def render_opencode_config(
    output_path: Path,
    providers: list[Any],
    default: Any | None = None,
    infra: CodeReviewSettings | None = None,
) -> Path:
    config = build_opencode_config_from_llm_providers(providers, default, infra)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return output_path
