import json

import pytest

from app.config import AgentSettings
from app.services.opencode_config import (
    build_opencode_config,
    materialize_opencode_config,
)
from app.services.review_env import require_review_env


def _full_settings(**overrides: object) -> AgentSettings:
    base = {
        "review_id": "550e8400-e29b-41d4-a716-446655440000",
        "repo_full_name": "org/repo",
        "pr_number": 7,
        "head_sha": "deadbeef",
        "github_token": "ghp_test",
        "llm_provider_id": "openai-compat",
        "llm_base_url": "https://api.example.com/v1",
        "llm_api_token": "sk-test",
        "llm_model": "gpt-4o",
        "opencode_model": "openai-compat/gpt-4o",
        "callback_url": "http://localhost:8000/api/v1/agent/review-events",
        "callback_secret": "dev-secret",
    }
    base.update(overrides)
    return AgentSettings(**base)


def test_build_opencode_config_from_settings() -> None:
    settings = _full_settings()
    config = build_opencode_config(settings)
    assert "openai-compat" in config["provider"]
    assert config["agent"]["code-reviewer"]["model"] == "openai-compat/gpt-4o"
    assert config["mcp"]["coreview"]["enabled"] is True
    assert config["tools"] == {"question": False}
    assert config["permission"]["question"] == "deny"
    assert config["permission"]["plan_enter"] == "deny"
    assert config["permission"]["plan_exit"] == "deny"
    agent = config["agent"]["code-reviewer"]
    assert agent["permission"]["bash"] == {"*": "allow"}
    assert agent["permission"]["task"] == "allow"
    assert agent["permission"]["question"] == "deny"
    assert agent["permission"]["doom_loop"] == "deny"
    assert agent["permission"]["plan_enter"] == "deny"


def test_build_opencode_config_uses_custom_system_prompt() -> None:
    settings = _full_settings(system_prompt="Review only Go files.")
    config = build_opencode_config(settings)
    assert config["agent"]["code-reviewer"]["prompt"] == "Review only Go files."


def test_materialize_opencode_config_writes_file() -> None:
    settings = _full_settings(review_id="unit-test-review")
    path = materialize_opencode_config(settings)
    try:
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["provider"]["openai-compat"]["options"]["apiKey"] == "sk-test"
    finally:
        path.unlink(missing_ok=True)


def test_require_review_env_accepts_full_settings() -> None:
    require_review_env(_full_settings())


def test_require_review_env_raises_when_missing_token() -> None:
    with pytest.raises(ValueError, match="NEXO_COREVIEW_GITHUB_TOKEN"):
        require_review_env(_full_settings(github_token=""))


def test_require_review_env_raises_when_missing_callback() -> None:
    with pytest.raises(ValueError, match="NEXO_COREVIEW_CALLBACK_URL"):
        require_review_env(_full_settings(callback_url=""))
