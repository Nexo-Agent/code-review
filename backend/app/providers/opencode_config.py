import json
from pathlib import Path
from typing import Any

from app.config import CodeReviewSettings, get_code_review_settings


def build_opencode_config(settings: CodeReviewSettings | None = None) -> dict[str, Any]:
    cfg = settings or get_code_review_settings()
    provider_id = cfg.llm_provider_id
    model_id = cfg.llm_model
    model_ref = cfg.resolved_opencode_model

    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            provider_id: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "OpenAI Compatible API",
                "options": {
                    "baseURL": "{env:NEXO_COREVIEW_LLM_BASE_URL}",
                    "apiKey": "{env:NEXO_COREVIEW_LLM_API_TOKEN}",
                },
                "models": {
                    model_id: {
                        "name": model_id,
                    }
                },
            }
        },
        "agent": {
            cfg.opencode_agent: {
                "description": "Reviews PR for bugs, security, and maintainability",
                "mode": "subagent",
                "model": model_ref,
                "prompt": (
                    "You are a code reviewer. Analyze the pull request diff and "
                    "return findings as JSON matching the outputFormat schema. "
                    "Focus on bugs, security issues, performance problems, and "
                    "missing tests. Do not suggest cosmetic changes unless they "
                    "hide real issues."
                ),
                "permission": {
                    "edit": "deny",
                    "write": "deny",
                    "bash": {
                        "git *": "allow",
                        "*": "deny",
                    },
                },
            }
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
