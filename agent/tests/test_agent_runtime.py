import asyncio
import json
from pathlib import Path

import pytest
from coreview_shared.agent.factory import build_review_agent
from coreview_shared.agent.models import OpenCodeRunConfig, ReviewAgentKind
from coreview_shared.agent.opencode import OpenCodeAgent
from coreview_shared.agent.opencode_config import (
    DEFAULT_CODE_REVIEWER_PROMPT,
    build_opencode_config,
    materialize_opencode_config,
)
from coreview_shared.review import PRContext, PRMetadata


def _opencode_config(**overrides: object) -> OpenCodeRunConfig:
    base = {
        "kind": ReviewAgentKind.OPENCODE,
        "review_id": "550e8400-e29b-41d4-a716-446655440000",
        "agent": "code-reviewer",
        "model": "openai-compat/gpt-4o",
        "timeout_seconds": 60,
        "log_level": "INFO",
        "llm_provider_id": "openai-compat",
        "llm_base_url": "https://api.example.com/v1",
        "llm_api_token": "sk-test",
        "llm_model": "gpt-4o",
        "system_prompt": "",
    }
    base.update(overrides)
    return OpenCodeRunConfig(**base)


def test_build_opencode_config_from_settings() -> None:
    config = build_opencode_config(_opencode_config())
    assert "openai-compat" in config["provider"]
    assert config["skills"]["paths"] == ["/opencode/skills"]
    assert config["agent"]["code-reviewer"]["model"] == "openai-compat/gpt-4o"
    assert config["mcp"]["coreview"]["enabled"] is True
    assert config["tools"] == {"question": False}
    assert config["permission"]["question"] == "deny"
    assert config["permission"]["plan_enter"] == "deny"
    assert config["permission"]["plan_exit"] == "deny"
    agent = config["agent"]["code-reviewer"]
    assert agent["mode"] == "primary"
    assert agent["permission"]["bash"] == {"*": "allow"}
    assert agent["permission"]["task"] == "allow"
    assert agent["permission"]["question"] == "deny"
    assert agent["permission"]["doom_loop"] == "deny"
    assert agent["permission"]["plan_enter"] == "deny"


def test_build_opencode_config_uses_custom_system_prompt() -> None:
    config = build_opencode_config(
        _opencode_config(system_prompt="Review only Go files.")
    )
    prompt = config["agent"]["code-reviewer"]["prompt"]
    assert DEFAULT_CODE_REVIEWER_PROMPT in prompt
    assert "Review only Go files." in prompt


def test_materialize_opencode_config_writes_file(tmp_path: Path) -> None:
    path = materialize_opencode_config(
        _opencode_config(review_id="unit-test-review"),
        output_path=tmp_path / "opencode.json",
    )
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["provider"]["openai-compat"]["options"]["apiKey"] == "sk-test"


def test_factory_returns_opencode_agent() -> None:
    agent = build_review_agent(ReviewAgentKind.OPENCODE, _opencode_config())
    assert isinstance(agent, OpenCodeAgent)


def test_factory_rejects_unsupported_runtime_kind() -> None:
    with pytest.raises(NotImplementedError, match="cursor-cli"):
        build_review_agent(
            ReviewAgentKind.CURSOR_CLI,
            _opencode_config(kind=ReviewAgentKind.CURSOR_CLI),
        )


def test_opencode_setup_and_teardown_manage_temp_config() -> None:
    agent = OpenCodeAgent(config=_opencode_config(review_id="temp-config"))

    async def run() -> Path:
        await agent.setup()
        path = agent._setup_artifacts.config_path
        assert path is not None and path.is_file()
        await agent.teardown()
        return path

    path = asyncio.run(run())
    assert not path.exists()


def test_opencode_parse_findings_from_json() -> None:
    provider = OpenCodeAgent(
        config=_opencode_config(model="anthropic/claude-sonnet-4-5")
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


def test_opencode_build_command_includes_log_flags() -> None:
    provider = OpenCodeAgent(config=_opencode_config(log_level="DEBUG"))
    cmd = provider._build_command("/workspaces/r1/repo")
    assert cmd[:5] == [
        "opencode",
        "--log-level",
        "DEBUG",
        "--print-logs",
        "run",
    ]
    assert "--format" in cmd
    assert cmd[cmd.index("--format") + 1] == "json"


def test_opencode_slim_prompt_includes_pr_context_and_schema() -> None:
    provider = OpenCodeAgent(config=_opencode_config(model="test/model"))
    context = PRContext(
        metadata=PRMetadata(
            repo_full_name="org/repo",
            pr_number=1,
            title="Test",
            author="dev",
            head_sha="a" * 40,
            base_sha="b" * 40,
            head_ref="feature",
            base_ref="main",
            html_url="https://github.com/org/repo/pull/1",
        ),
        diff="diff content",
    )
    prompt = provider._build_prompt(context)
    assert "Review pull request #1: Test" in prompt
    assert "org/repo" in prompt
    assert '"findings"' in prompt
    assert "diff content" not in prompt
    assert "Focus on bugs, security, performance" not in prompt


def test_opencode_parse_ndjson_stream_collects_step_finish_tokens() -> None:
    provider = OpenCodeAgent(config=_opencode_config(model="test/model"))
    stdout = "\n".join(
        [
            '{"type":"step_start","part":{"type":"step-start"}}',
            (
                '{"type":"step_finish","part":{"type":"step-finish","reason":"tool-calls",'
                '"tokens":{"input":100,"output":25,"total":125}}}'
            ),
            (
                '{"type":"text","part":{"type":"text","text":'
                '"```json\\n{\\"findings\\": [{\\"severity\\": \\"warning\\", '
                '\\"title\\": \\"Bug\\", \\"body\\": \\"details\\"}]}\\n```"}}'
            ),
            (
                '{"type":"step_finish","part":{"type":"step-finish","reason":"stop",'
                '"tokens":{"input":50,"output":10,"total":60}}}'
            ),
        ]
    )
    for line in stdout.splitlines():
        provider._log_stdout_event(line)
    assert len(provider._llm_calls) == 2
    assert provider._llm_calls[0].total_tokens == 125
    assert provider._llm_calls[1].total_tokens == 60
    findings = provider._parse_cli_output(stdout)
    assert len(findings) == 1
    assert findings[0].title == "Bug"


def test_opencode_parse_ndjson_stream_ignores_tool_events() -> None:
    provider = OpenCodeAgent(config=_opencode_config(model="test/model"))
    stdout = "\n".join(
        [
            '{"type":"step_start","part":{"type":"step-start"}}',
            (
                '{"type":"tool_use","part":{"type":"tool",'
                '"tool":"coreview_coreview-ci_get_summary","output":"{}"}}'
            ),
            (
                '{"type":"text","part":{"type":"text","text":'
                '"```json\\n{\\"findings\\": [{\\"severity\\": \\"warning\\", '
                '\\"title\\": \\"Bug\\", \\"body\\": \\"details\\"}]}\\n```"}}'
            ),
        ]
    )
    findings = provider._parse_cli_output(stdout)
    assert len(findings) == 1
    assert findings[0].title == "Bug"


def test_opencode_parse_ndjson_stream_without_findings_returns_empty() -> None:
    provider = OpenCodeAgent(config=_opencode_config(model="test/model"))
    stdout = (
        '{"type":"tool_use","part":{"type":"tool","output":"ignored"}}\n'
        '{"type":"step_finish","part":{"type":"step-finish"}}'
    )
    assert provider._parse_cli_output(stdout) == []


def test_opencode_pump_stream_handles_long_lines() -> None:
    provider = OpenCodeAgent(config=_opencode_config(model="test/model"))
    long_text = "x" * 10000
    payload = (
        '{"type":"text","part":{"type":"text","text":"'
        + long_text
        + '"}}\n{"type":"step_finish"}\n'
    ).encode("utf-8")

    async def run() -> tuple[list[bytes], list[str]]:
        reader = asyncio.StreamReader(limit=32)
        chunks: list[bytes] = []
        lines: list[str] = []
        reader.feed_data(payload)
        reader.feed_eof()
        await provider._pump_stream(reader, chunks, lines.append)
        return chunks, lines

    chunks, lines = asyncio.run(run())
    assert b"".join(chunks) == payload
    assert len(lines) == 2
    assert long_text in lines[0]
    assert lines[1] == '{"type":"step_finish"}'
