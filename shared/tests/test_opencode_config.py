from coreview_shared.agent.opencode_config import (
    DEFAULT_CODE_REVIEWER_PROMPT,
    HEADLESS_DENIED_PERMISSIONS,
    build_code_reviewer_agent_config,
    build_headless_opencode_permissions,
    build_headless_opencode_tools,
    build_mcp_config,
    build_review_agent_permissions,
    build_review_skills_config,
    llm_provider_block,
)


def test_headless_denied_permissions_include_plan_and_question() -> None:
    assert HEADLESS_DENIED_PERMISSIONS["question"] == "deny"
    assert HEADLESS_DENIED_PERMISSIONS["plan_enter"] == "deny"
    assert HEADLESS_DENIED_PERMISSIONS["plan_exit"] == "deny"
    assert HEADLESS_DENIED_PERMISSIONS["doom_loop"] == "deny"


def test_headless_permissions_override_ask_defaults() -> None:
    perms = build_headless_opencode_permissions()
    assert perms["external_directory"] == "deny"
    assert perms["bash"] == {"*": "allow"}
    assert perms["task"] == "allow"
    assert perms["todowrite"] == "allow"


def test_headless_tools_disable_only_question() -> None:
    tools = build_headless_opencode_tools()
    assert tools == {"question": False}
    assert "bash" not in tools


def test_review_skills_config_points_at_bundled_path() -> None:
    skills = build_review_skills_config()
    assert skills["paths"] == ["/opencode/skills"]


def test_mcp_config_uses_stdio_subprocess() -> None:
    mcp = build_mcp_config()
    assert mcp["coreview"]["type"] == "local"
    assert mcp["coreview"]["command"] == ["cogito-review-agent", "serve"]
    assert mcp["coreview"]["enabled"] is True


def test_review_agent_config_appends_custom_prompt() -> None:
    agent = build_code_reviewer_agent_config(
        "code-reviewer",
        prompt="Always respond in Vietnamese",
    )
    assert DEFAULT_CODE_REVIEWER_PROMPT in agent["prompt"]
    assert "Always respond in Vietnamese" in agent["prompt"]


def test_review_agent_config_is_primary_agent() -> None:
    agent = build_code_reviewer_agent_config("code-reviewer")
    assert agent["mode"] == "primary"


def test_review_agent_config_allows_operational_tools() -> None:
    agent = build_code_reviewer_agent_config("code-reviewer")
    perms = build_review_agent_permissions()
    assert agent["permission"] == perms
    assert perms["bash"] == {"*": "allow"}
    assert perms["task"] == "allow"
    assert perms["todowrite"] == "allow"
    assert perms["edit"] == "deny"
    assert perms["plan_enter"] == "deny"
    assert perms["question"] == "deny"
    assert agent["tools"]["coreview-git_fetch_pr_context"] is True
    assert agent["tools"]["question"] is False


def test_llm_provider_block_groq_uses_native_npm() -> None:
    block = llm_provider_block(
        "groq",
        "llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key="gsk_test",
    )
    provider = block["groq"]
    assert provider["npm"] == "@ai-sdk/groq"
    assert provider["name"] == "Groq"
    assert provider["options"]["apiKey"] == "gsk_test"
    assert "baseURL" not in provider["options"]


def test_llm_provider_block_openrouter_uses_openrouter_sdk() -> None:
    block = llm_provider_block(
        "openrouter",
        "anthropic/claude-sonnet-4",
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-or-test",
    )
    provider = block["openrouter"]
    assert provider["npm"] == "@openrouter/ai-sdk-provider"
    assert provider["name"] == "OpenRouter"
    assert "baseURL" not in provider["options"]


def test_llm_provider_block_fireworks_uses_openai_compatible_with_base_url() -> None:
    block = llm_provider_block(
        "fireworks-ai",
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
        base_url="https://api.fireworks.ai/inference/v1",
        api_key="fw_test",
    )
    provider = block["fireworks-ai"]
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert provider["options"]["baseURL"] == "https://api.fireworks.ai/inference/v1"


def test_llm_provider_block_unknown_falls_back_to_openai_compatible() -> None:
    block = llm_provider_block(
        "openai-compat",
        "my-model",
        base_url="https://llm.example.com/v1",
        api_key="sk_test",
    )
    provider = block["openai-compat"]
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert provider["name"] == "OpenAI Compatible API"
    assert provider["options"]["baseURL"] == "https://llm.example.com/v1"
