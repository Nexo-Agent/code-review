"""OpenCode configuration builders shared by backend and agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Permissions that prompt for user input — deny in headless `opencode run`.
# Ref: opencode.ai/docs/permissions , packages/opencode run.ts
HEADLESS_DENIED_PERMISSIONS: dict[str, str] = {
    "question": "deny",
    "doom_loop": "deny",
    "plan_enter": "deny",
    "plan_exit": "deny",
    "ask_exit": "deny",
    "terminal_start": "deny",
    "terminal_stop": "deny",
    "pty_start": "deny",
    "pty_exec": "deny",
    "pty_stop": "deny",
}

# OpenCode defaults these to "ask" — override for unattended review runs.
HEADLESS_ASK_DEFAULT_OVERRIDES: dict[str, str] = {
    "external_directory": "deny",
}

# Operational tools: auto-allow (no approval prompt). File edits stay denied.
HEADLESS_AUTO_ALLOW_PERMISSIONS: dict[str, Any] = {
    "read": "allow",
    "grep": "allow",
    "glob": "allow",
    "list": "allow",
    "bash": {"*": "allow"},
    "task": "allow",
    "todowrite": "allow",
    "skill": "allow",
    "webfetch": "allow",
    "websearch": "allow",
    "lsp": "allow",
}

# Legacy `tools` toggles — only disable tools that block on user input.
HEADLESS_DISABLED_TOOLS: dict[str, bool] = {
    "question": False,
}


def build_headless_opencode_tools() -> dict[str, bool]:
    """Global tool toggles (legacy `tools` field; still honored by OpenCode)."""
    return dict(HEADLESS_DISABLED_TOOLS)


def build_headless_opencode_permissions() -> dict[str, Any]:
    """Global permissions for non-interactive review runs."""
    return {
        **HEADLESS_AUTO_ALLOW_PERMISSIONS,
        **HEADLESS_ASK_DEFAULT_OVERRIDES,
        **HEADLESS_DENIED_PERMISSIONS,
    }


def build_review_agent_tools() -> dict[str, bool]:
    """Explicit MCP tools; disable only user-interrupt tools."""
    return {
        "coreview-git_fetch_pr_context": True,
        "coreview-ci_get_summary": True,
        **HEADLESS_DISABLED_TOOLS,
    }


def build_review_agent_permissions() -> dict[str, Any]:
    """Read-only review agent: allow operational tools, deny edits and prompts."""
    return {
        "edit": "deny",
        "write": "deny",
        **build_headless_opencode_permissions(),
    }


def build_mcp_config() -> dict[str, Any]:
    """Configure coreview MCP as a local stdio subprocess for `opencode run`."""
    return {
        "coreview": {
            "type": "local",
            "command": ["cogito-review-agent", "serve"],
            "enabled": True,
        }
    }


DEFAULT_CODE_REVIEWER_PROMPT = (
    "You are a code reviewer. Use MCP tools to gather context "
    "before reviewing: call coreview-git_fetch_pr_context and "
    "coreview-ci_get_summary with the repository and PR details "
    "from the prompt. Analyze the PR git worktree at the session "
    "directory. Use the bash tool to run project lint, typecheck, and "
    "unit tests (see AGENTS.md, Makefile, package.json, CI workflows). "
    "Trace blast radius: grep for callers and cross-layer impact beyond "
    "the diff. Do not modify files or post remote comments via MCP. "
    "Return findings as JSON matching the outputFormat schema in your "
    "final response. Focus on bugs, security issues, performance "
    "problems, missing tests, and failures from validation commands. "
    "Do not enter plan mode or ask the user questions — complete the "
    "review autonomously."
)

# Bundled into the agent image at agent/Dockerfile COPY agent/skills/ /opencode/skills/
CODE_REVIEWER_SKILLS_PATH = "/opencode/skills"


def build_review_skills_config() -> dict[str, Any]:
    """Register bundled review skills for OpenCode discovery."""
    return {
        "paths": [CODE_REVIEWER_SKILLS_PATH],
    }


def build_code_reviewer_agent_config(
    agent_name: str,
    *,
    prompt: str | None = None,
) -> dict[str, Any]:
    custom = prompt.strip() if prompt else ""
    resolved_prompt = DEFAULT_CODE_REVIEWER_PROMPT
    if custom:
        resolved_prompt = f"{DEFAULT_CODE_REVIEWER_PROMPT}\n\n{custom}"

    return {
        "description": "Reviews PR for bugs, security, and maintainability",
        "mode": "primary",
        "tools": build_review_agent_tools(),
        "permission": build_review_agent_permissions(),
        "prompt": resolved_prompt,
    }


@dataclass(frozen=True, slots=True)
class OpenCodeLlmProviderSpec:
    npm: str
    name: str
    uses_base_url: bool


# Provider IDs and npm packages aligned with models.dev / OpenCode built-ins.
OPENCODE_LLM_PROVIDERS: dict[str, OpenCodeLlmProviderSpec] = {
    "mistral": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/mistral",
        name="Mistral",
        uses_base_url=False,
    ),
    "cohere": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/cohere",
        name="Cohere",
        uses_base_url=False,
    ),
    "openrouter": OpenCodeLlmProviderSpec(
        npm="@openrouter/ai-sdk-provider",
        name="OpenRouter",
        uses_base_url=False,
    ),
    "togetherai": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/togetherai",
        name="Together AI",
        uses_base_url=False,
    ),
    "fireworks-ai": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/openai-compatible",
        name="Fireworks AI",
        uses_base_url=True,
    ),
    "groq": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/groq",
        name="Groq",
        uses_base_url=False,
    ),
    "deepinfra": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/deepinfra",
        name="Deep Infra",
        uses_base_url=False,
    ),
    "moonshotai": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/openai-compatible",
        name="Moonshot AI",
        uses_base_url=True,
    ),
    "moonshotai-cn": OpenCodeLlmProviderSpec(
        npm="@ai-sdk/openai-compatible",
        name="Moonshot AI (China)",
        uses_base_url=True,
    ),
}


def llm_provider_block(
    provider_id: str,
    model_id: str,
    *,
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    spec = OPENCODE_LLM_PROVIDERS.get(provider_id)
    npm = spec.npm if spec else "@ai-sdk/openai-compatible"
    name = spec.name if spec else "OpenAI Compatible API"
    options: dict[str, str] = {"apiKey": api_key}
    if spec is None or spec.uses_base_url:
        options["baseURL"] = base_url

    return {
        provider_id: {
            "npm": npm,
            "name": name,
            "options": options,
            "models": {
                model_id: {
                    "name": model_id,
                }
            },
        }
    }
