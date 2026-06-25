from coreview_shared.opencode.config import (
    DEFAULT_CODE_REVIEWER_PROMPT,
    HEADLESS_DENIED_PERMISSIONS,
    build_code_reviewer_agent_config,
    build_headless_opencode_permissions,
    build_headless_opencode_tools,
    build_review_agent_permissions,
    build_review_skills_config,
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
