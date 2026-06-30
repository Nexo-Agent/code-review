from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ReviewAgentKind(StrEnum):
    OPENCODE = "opencode"
    CURSOR_CLI = "cursor-cli"
    CLAUDE_CODE = "claude-code"
    OPENCLAUDE = "openclaude"


@dataclass(frozen=True, slots=True)
class AgentRunConfig:
    kind: ReviewAgentKind


@dataclass(frozen=True, slots=True)
class OpenCodeRunConfig(AgentRunConfig):
    review_id: str
    agent: str
    model: str
    timeout_seconds: int
    log_level: str
    llm_provider_id: str
    llm_base_url: str
    llm_api_token: str
    llm_model: str
    system_prompt: str = ""


@dataclass(frozen=True, slots=True)
class AgentSetupArtifacts:
    config_path: Path | None = None
