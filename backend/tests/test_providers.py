import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import CodeReviewSettings
from app.providers.git.diff_lines import filter_inline_comments, parse_commentable_lines
from app.providers.git.github import HANDLED_WEBHOOK_ACTIONS, GitHubProvider
from app.providers.protocols import (
    InlineComment,
    InlineCommentsResult,
    Workspace,
    WorkspaceSpec,
)
from app.providers.runtime.docker.command_runner import DockerCommandRunner


def test_github_webhook_signature_valid() -> None:
    secret = "test-secret"
    payload = b'{"action":"opened"}'
    signature = (
        "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    )
    provider = GitHubProvider(token="")
    assert provider.verify_webhook_signature(payload, signature, secret)


def test_github_webhook_signature_invalid() -> None:
    provider = GitHubProvider(token="")
    assert not provider.verify_webhook_signature(b"{}", "sha256=deadbeef", "secret")
    assert not provider.verify_webhook_signature(b"{}", None, "secret")
    assert not provider.verify_webhook_signature(b"{}", "sha256=abc", "")


def test_github_parse_webhook_valid() -> None:
    provider = GitHubProvider(token="")
    body = json.dumps(
        {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "head": {"sha": "abc123"},
            },
            "repository": {"full_name": "org/repo"},
        }
    ).encode()
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "delivery-1",
    }
    event = provider.parse_webhook(headers, body)
    assert event is not None
    assert event.repo_full_name == "org/repo"
    assert event.pr_number == 42
    assert event.head_sha == "abc123"
    assert event.delivery_id == "delivery-1"


def test_github_parse_webhook_ignored_event() -> None:
    provider = GitHubProvider(token="")
    body = b"{}"
    assert provider.parse_webhook({"X-GitHub-Event": "push"}, body) is None


@pytest.mark.asyncio
async def test_github_clone_repository() -> None:
    provider = GitHubProvider(token="tok")
    runner = AsyncMock()
    spec = WorkspaceSpec(
        review_id="r1",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="deadbeef",
    )
    from pathlib import Path

    workspace = Workspace(path=Path("/workspaces/r1"), spec=spec)
    await provider.clone_repository(spec, workspace, runner)

    assert runner.run.await_count == 3
    clone_args = runner.run.await_args_list[0].args[0]
    assert "github.com/org/repo.git" in clone_args[4]
    assert clone_args[0] == "git"


@pytest.mark.asyncio
async def test_github_post_inline_comments() -> None:
    provider = GitHubProvider(token="tok")
    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value.raise_for_status = MagicMock()
        client_cls.return_value = client

        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -8,3 +8,4 @@
 context
 unchanged
+added line
"""
        result = await provider.post_inline_comments(
            "org/repo",
            1,
            "sha123",
            [InlineComment(path="a.py", line=10, body="issue")],
            diff=diff,
        )

        client.post.assert_awaited_once()
        call_kwargs = client.post.await_args.kwargs
        assert "reviews" in client.post.await_args.args[0]
        assert call_kwargs["json"]["comments"][0]["path"] == "a.py"
        assert isinstance(result, InlineCommentsResult)
        assert len(result.posted) == 1


@pytest.mark.asyncio
async def test_github_post_inline_comments_skips_lines_outside_diff() -> None:
    provider = GitHubProvider(token="tok")
    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client_cls.return_value = client

        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 x
+y
"""
        result = await provider.post_inline_comments(
            "org/repo",
            1,
            "sha123",
            [InlineComment(path="a.py", line=99, body="not in diff")],
            diff=diff,
        )

        client.post.assert_not_awaited()
        assert result.posted == ()
        assert len(result.skipped) == 1


@pytest.mark.asyncio
async def test_github_post_inline_comments_422_fallback() -> None:
    provider = GitHubProvider(token="tok")
    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client_cls.return_value = client

        bad = httpx.Response(422, request=MagicMock(), text="not in hunk")
        good = MagicMock()
        good.raise_for_status = MagicMock()

        client.post.side_effect = [
            httpx.HTTPStatusError("batch", request=MagicMock(), response=bad),
            httpx.HTTPStatusError("single bad", request=MagicMock(), response=bad),
            good,
        ]

        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 x
+y
"""
        comments = [
            InlineComment(path="a.py", line=2, body="bad"),
            InlineComment(path="a.py", line=1, body="ok"),
        ]
        result = await provider.post_inline_comments(
            "org/repo",
            1,
            "sha123",
            comments,
            diff=diff,
        )

        assert client.post.await_count == 3
        assert len(result.posted) == 1
        assert len(result.skipped) == 1


def test_parse_commentable_lines() -> None:
    diff = """diff --git a/src/foo.py b/src/foo.py
--- a/src/foo.py
+++ b/src/foo.py
@@ -10,4 +10,5 @@
 ctx
-old
+new
 tail
"""
    lines = parse_commentable_lines(diff)
    assert ("src/foo.py", 12, "RIGHT") in lines
    assert ("src/foo.py", 11, "LEFT") in lines


def test_filter_inline_comments() -> None:
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 x
+y
"""
    comments = [
        InlineComment(path="a.py", line=2, body="ok"),
        InlineComment(path="a.py", line=50, body="skip"),
    ]
    valid, skipped = filter_inline_comments(comments, diff)
    assert len(valid) == 1
    assert valid[0].line == 2
    assert len(skipped) == 1


def test_build_opencode_config_includes_mcp() -> None:
    from app.providers.opencode_config import build_opencode_config

    cfg = CodeReviewSettings()
    config = build_opencode_config(cfg)
    assert "mcp" in config
    assert config["mcp"]["coreview"]["type"] == "local"
    assert config["mcp"]["coreview"]["command"] == [
        "coreview-agent",
        "serve",
        "--transport",
        "stdio",
    ]
    assert config["tools"]["bash"] is False
    agent = config["agent"]["code-reviewer"]
    assert agent["tools"]["coreview-git_fetch_pr_context"] is True
    assert agent["tools"]["coreview-ci_get_summary"] is True
    assert agent["permission"]["bash"]["*"] == "deny"


def test_build_opencode_config_uses_openai_compatible_provider() -> None:
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
    from app.providers.factory import build_providers

    providers = build_providers(
        CodeReviewSettings(
            git_provider="github",
            runtime_provider="docker",
        )
    )
    assert providers.git is not None
    assert providers.runtime is not None
    with patch("app.providers.runtime.docker.provider.get_docker_client") as get_client:
        get_client.return_value = MagicMock()
        assert providers.runtime.command_runner() is not None


def test_provider_factory_unsupported_git() -> None:
    from app.providers.factory import build_providers

    with pytest.raises(NotImplementedError):
        build_providers(CodeReviewSettings(git_provider="gitlab"))


def test_docker_command_runner_invokes_client() -> None:
    from pathlib import Path

    client = MagicMock()
    runner = DockerCommandRunner(
        client=client,
        git_image="alpine/git:latest",
        workspace_root=Path("/workspaces"),
    )
    import asyncio

    asyncio.run(runner.run(["git", "version"], Path("/workspaces/r1")))
    client.containers.run.assert_called_once()
    args, kwargs = client.containers.run.call_args
    assert args[0] == "alpine/git:latest"
    assert kwargs["command"] == ["version"]
    assert kwargs["entrypoint"] == ["git"]
    assert kwargs["remove"] is True


def test_docker_client_uses_explicit_host() -> None:
    from app.providers.runtime.docker import client as docker_client

    docker_client.reset_docker_client()
    mock_client = MagicMock()
    mock_client.ping = MagicMock()

    with patch.object(
        docker_client.docker, "DockerClient", return_value=mock_client
    ) as ctor:
        client = docker_client.get_docker_client("unix:///custom.sock")

    assert client is mock_client
    ctor.assert_called_once_with(base_url="unix:///custom.sock")
    docker_client.reset_docker_client()


def test_handled_webhook_actions() -> None:
    assert "opened" in HANDLED_WEBHOOK_ACTIONS
    assert "closed" not in HANDLED_WEBHOOK_ACTIONS
