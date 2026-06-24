import json
from pathlib import Path
from typing import Any

from app.config import CodeReviewSettings, get_code_review_settings
from app.providers.mcp_config import (
    build_code_reviewer_agent_config,
    build_mcp_config,
)


def _llm_provider_block(
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


def build_opencode_config(settings: CodeReviewSettings | None = None) -> dict[str, Any]:
    cfg = settings or get_code_review_settings()
    agent_name = cfg.opencode_agent
    agent_cfg = build_code_reviewer_agent_config(agent_name)
    agent_cfg["model"] = cfg.resolved_opencode_model

    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": build_mcp_config(cfg),
        "tools": {
            "bash": False,
        },
        "provider": _llm_provider_block(
            cfg.llm_provider_id,
            cfg.llm_model,
            base_url="{env:NEXO_COREVIEW_LLM_BASE_URL}",
            api_key="{env:NEXO_COREVIEW_LLM_API_TOKEN}",
        ),
        "agent": {
            agent_name: agent_cfg,
        },
    }


def merge_llm_provider_blocks(
    providers: list[Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for row in providers:
        block = _llm_provider_block(
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
    elif providers:
        agent_cfg["model"] = providers[0].resolved_opencode_model
    else:
        agent_cfg["model"] = infra.resolved_opencode_model

    provider_blocks = merge_llm_provider_blocks(providers) if providers else build_opencode_config(infra)["provider"]

    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": build_mcp_config(infra),
        "tools": {
            "bash": False,
        },
        "provider": provider_blocks,
        "agent": {
            agent_name: agent_cfg,
        },
    }


def build_opencode_config_from_integration_row(
    integration: Any,
    infra: CodeReviewSettings | None = None,
) -> dict[str, Any]:
    """Deprecated: build from legacy singleton row shape."""
    infra = infra or get_code_review_settings()
    agent_name = infra.opencode_agent
    agent_cfg = build_code_reviewer_agent_config(agent_name)
    agent_cfg["model"] = integration.resolved_opencode_model

    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": build_mcp_config(infra),
        "tools": {
            "bash": False,
        },
        "provider": _llm_provider_block(
            integration.llm_provider_id,
            integration.llm_model,
            base_url=integration.llm_base_url,
            api_key=integration.llm_api_token,
        ),
        "agent": {
            agent_name: agent_cfg,
        },
    }


def render_opencode_config(
    output_path: Path,
    settings: CodeReviewSettings | None = None,
) -> Path:
    if settings is None:
        settings = get_code_review_settings()

    config = build_opencode_config(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return output_path
