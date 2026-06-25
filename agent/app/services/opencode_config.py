"""OpenCode config materialization from injected env vars."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from coreview_shared.opencode.config import (
    build_code_reviewer_agent_config,
    build_headless_opencode_permissions,
    build_headless_opencode_tools,
    build_mcp_config,
    llm_provider_block,
)

from app.config import AgentSettings

logger = logging.getLogger(__name__)


def build_opencode_config(settings: AgentSettings) -> dict[str, Any]:
    agent_name = settings.opencode_agent
    agent_cfg = build_code_reviewer_agent_config(
        agent_name,
        prompt=settings.system_prompt or None,
    )
    agent_cfg["model"] = settings.resolved_opencode_model

    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": build_mcp_config(),
        "tools": build_headless_opencode_tools(),
        "permission": build_headless_opencode_permissions(),
        "provider": llm_provider_block(
            settings.llm_provider_id,
            settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_token,
        ),
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
    if settings.system_prompt.strip():
        logger.info(
            "Materialized OpenCode config with custom system prompt (%d chars) at %s",
            len(settings.system_prompt.strip()),
            path,
        )
    else:
        logger.info("Materialized OpenCode config at %s", path)
    return path
