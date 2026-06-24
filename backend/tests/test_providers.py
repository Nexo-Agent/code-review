import hashlib
import hmac

import pytest

from app.providers.git.github import GitHubProvider
from app.providers.llm.opencode import OpenCodeLLMProvider


def test_github_webhook_signature_valid() -> None:
    secret = "test-secret"
    payload = b'{"action":"opened"}'
    signature = (
        "sha256="
        + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    )
    provider = GitHubProvider(token="")
    assert provider.verify_webhook_signature(payload, signature, secret)


def test_github_webhook_signature_invalid() -> None:
    provider = GitHubProvider(token="")
    assert not provider.verify_webhook_signature(
        b"{}", "sha256=deadbeef", "secret"
    )
    assert not provider.verify_webhook_signature(b"{}", None, "secret")
    assert not provider.verify_webhook_signature(b"{}", "sha256=abc", "")


def test_opencode_parse_findings_from_json() -> None:
    provider = OpenCodeLLMProvider(
        server_url="http://localhost:4096",
        username="opencode",
        password="",
        agent="code-reviewer",
        model="anthropic/claude-sonnet-4-5",
        timeout_seconds=60,
    )
    data = {
        "findings": [
            {
                "severity": "warning",
                "title": "Missing null check",
                "body": "Variable may be None",
                "file_path": "app/main.py",
                "line_start": 10,
            }
        ]
    }
    findings = provider._parse_findings(data)
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].file_path == "app/main.py"


def test_opencode_parse_findings_from_markdown_json() -> None:
    provider = OpenCodeLLMProvider(
        server_url="http://localhost:4096",
        username="opencode",
        password="",
        agent="code-reviewer",
        model="anthropic/claude-sonnet-4-5",
        timeout_seconds=60,
    )
    text = """Here are findings:
```json
{"findings": [{"severity": "info", "title": "Note", "body": "Consider refactor"}]}
```"""
    findings = provider._parse_findings_from_text(text)
    assert len(findings) == 1
    assert findings[0].title == "Note"


def test_build_opencode_config_uses_openai_compatible_provider() -> None:
    from app.config import CodeReviewSettings
    from app.providers.opencode_config import build_opencode_config

    cfg = CodeReviewSettings(
        llm_provider_id="openai-compat",
        llm_base_url="https://llm.example.com/v1",
        llm_api_token="secret",
        llm_model="my-model",
        opencode_model="",
    )
    config = build_opencode_config(cfg)
    provider = config["provider"]["openai-compat"]
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert provider["options"]["baseURL"] == "{env:NEXO_COREVIEW_LLM_BASE_URL}"
    assert provider["options"]["apiKey"] == "{env:NEXO_COREVIEW_LLM_API_TOKEN}"
    assert "my-model" in provider["models"]
    assert config["agent"]["code-reviewer"]["model"] == "openai-compat/my-model"


def test_resolved_opencode_model_override() -> None:
    from app.config import CodeReviewSettings

    cfg = CodeReviewSettings(
        llm_model="gpt-4o",
        opencode_model="custom/other",
    )
    assert cfg.resolved_opencode_model == "custom/other"


def test_provider_factory_github_docker() -> None:
    from app.config import CodeReviewSettings
    from app.providers.factory import build_providers

    providers = build_providers(
        CodeReviewSettings(
            git_provider="github",
            runtime_provider="docker",
        )
    )
    assert providers.git is not None
    assert providers.llm is not None


def test_provider_factory_unsupported_git() -> None:
    from app.config import CodeReviewSettings
    from app.providers.factory import build_providers

    with pytest.raises(NotImplementedError):
        build_providers(CodeReviewSettings(git_provider="gitlab"))
