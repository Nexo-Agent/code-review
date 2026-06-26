import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from coreview_shared.protocols import (
    InlineComment,
    InlineCommentsResult,
    PreparedWorkspace,
    Workspace,
    WorkspaceSpec,
)
from coreview_shared.providers.git.diff_lines import (
    filter_inline_comments,
    parse_commentable_lines,
)
from coreview_shared.providers.git.github import HANDLED_WEBHOOK_ACTIONS, GitHubProvider
from coreview_shared.runtime.docker.command_runner import DockerCommandRunner

from app.config import CodeReviewSettings, ReviewRuntimeConfig


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
async def test_github_ensure_worktree() -> None:
    provider = GitHubProvider(token="tok")
    runner = AsyncMock()
    spec = WorkspaceSpec(
        review_id="r1",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="deadbeef0123456789deadbeef0123456789",
    )
    repo_base = Path("/workspaces/github/org__repo")
    expected = repo_base / "worktrees" / "pr-1-deadbee"
    prepared_workspace = PreparedWorkspace(
        repo_base=repo_base,
        mirror_path=repo_base / "mirror.git",
        worktree_path=expected,
        workspace=Workspace(path=expected, spec=spec),
    )

    with patch.object(
        provider._workspace_adapter,
        "prepare_workspace",
        new=AsyncMock(return_value=prepared_workspace),
    ) as mock_prepare:
        path = await provider.ensure_worktree(spec, repo_base, runner)

    assert path == expected
    mock_prepare.assert_awaited_once()
    access = mock_prepare.await_args.args[3]
    assert access.clone_url == "https://x-access-token:tok@github.com/org/repo.git"


@pytest.mark.asyncio
async def test_github_prepare_review_prefers_local_diff() -> None:
    provider = GitHubProvider(token="tok")
    runner = AsyncMock()
    spec = WorkspaceSpec(
        review_id="r1",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="head-sha",
    )
    repo_base = Path("/workspaces/github/org__repo")
    prepared_workspace = PreparedWorkspace(
        repo_base=repo_base,
        mirror_path=repo_base / "mirror.git",
        worktree_path=repo_base / "worktrees" / "pr-1-headsha",
        workspace=Workspace(path=repo_base / "worktrees" / "pr-1-headsha", spec=spec),
    )

    with (
        patch.object(
            provider,
            "get_pr_metadata",
            new=AsyncMock(
                return_value=MagicMock(
                    repo_full_name="org/repo",
                    pr_number=1,
                    title="PR",
                    author="alice",
                    head_sha="head-sha",
                    base_sha="base-sha",
                    head_ref="feature",
                    base_ref="main",
                    html_url="https://example.com/pr/1",
                )
            ),
        ),
        patch.object(
            provider._workspace_adapter,
            "prepare_workspace",
            new=AsyncMock(return_value=prepared_workspace),
        ) as mock_prepare,
        patch.object(
            provider._workspace_adapter,
            "build_diff",
            new=AsyncMock(return_value="local diff"),
        ) as mock_diff,
    ):
        review = await provider.prepare_review(spec, repo_base, runner)

    assert review.context.diff == "local diff"
    assert review.workspace == prepared_workspace
    mock_prepare.assert_awaited_once()
    mock_diff.assert_awaited_once()


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
    from app.providers.opencode_config import build_opencode_config_from_llm_providers

    config = build_opencode_config_from_llm_providers([], None, CodeReviewSettings())
    assert "mcp" in config
    assert config["mcp"]["coreview"]["type"] == "local"
    assert config["mcp"]["coreview"]["command"] == ["cogito-review-agent", "serve"]
    assert config["tools"] == {"question": False}
    assert config["permission"]["question"] == "deny"
    assert config["permission"]["doom_loop"] == "deny"
    assert config["permission"]["plan_enter"] == "deny"
    assert config["permission"]["plan_exit"] == "deny"
    assert config["permission"]["external_directory"] == "deny"
    assert config["permission"]["bash"] == {"*": "allow"}
    assert config["permission"]["task"] == "allow"
    agent = config["agent"]["code-reviewer"]
    assert agent["tools"]["coreview-git_fetch_pr_context"] is True
    assert agent["tools"]["coreview-ci_get_summary"] is True
    assert agent["tools"]["question"] is False
    assert agent["permission"]["bash"] == {"*": "allow"}
    assert agent["permission"]["task"] == "allow"
    assert agent["permission"]["todowrite"] == "allow"
    assert agent["permission"]["edit"] == "deny"
    assert agent["permission"]["question"] == "deny"
    assert agent["permission"]["doom_loop"] == "deny"
    assert agent["permission"]["plan_enter"] == "deny"
    assert agent["permission"]["plan_exit"] == "deny"


def test_build_opencode_config_uses_openai_compatible_provider() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.providers.opencode_config import build_opencode_config_from_llm_providers
    from app.repositories.llm_providers import LlmProviderRow

    now = datetime.now(UTC)
    llm = LlmProviderRow(
        id=uuid4(),
        name="Default",
        provider_id="openai-compat",
        base_url="https://llm.example.com/v1",
        api_token="secret",
        model="my-model",
        opencode_model="",
        is_default=True,
        created_at=now,
        updated_at=now,
    )
    config = build_opencode_config_from_llm_providers([llm], llm)
    provider = config["provider"]["openai-compat"]
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert provider["options"]["baseURL"] == "https://llm.example.com/v1"
    assert provider["options"]["apiKey"] == "secret"
    assert "my-model" in provider["models"]
    assert config["agent"]["code-reviewer"]["model"] == "openai-compat/my-model"


def test_provider_factory_github_docker() -> None:
    from app.providers.factory import build_providers

    runtime = ReviewRuntimeConfig(
        git_provider="github",
        github_webhook_secret="",
        github_token="",
        llm_provider_id="openai-compat",
        llm_base_url="https://api.openai.com/v1",
        llm_api_token="",
        llm_model="gpt-4o",
    )
    providers = build_providers(
        runtime,
        infra=CodeReviewSettings(runtime_provider="docker"),
    )
    assert providers.git is not None
    assert providers.runtime is not None
    with patch(
        "coreview_shared.runtime.docker.provider.get_docker_client"
    ) as get_client:
        get_client.return_value = MagicMock()
        assert providers.runtime.command_runner() is not None


def test_provider_factory_azure_devops() -> None:
    from coreview_shared.providers.ci.noop import NoOpCIProvider
    from coreview_shared.providers.git.azure_devops import AzureDevOpsProvider

    from app.providers.factory import build_providers

    runtime = ReviewRuntimeConfig(
        git_provider="azure-devops",
        github_webhook_secret="",
        github_token="",
        llm_provider_id="openai-compat",
        llm_base_url="https://api.openai.com/v1",
        llm_api_token="",
        llm_model="gpt-4o",
        ado_organization="fabrikam",
        ado_project="MyProject",
        ado_pat="pat",
    )
    providers = build_providers(runtime)
    assert isinstance(providers.git, AzureDevOpsProvider)
    assert isinstance(providers.ci, NoOpCIProvider)


def test_provider_factory_unsupported_git() -> None:
    from app.providers.factory import build_providers

    runtime = ReviewRuntimeConfig(
        git_provider="gitlab",
        github_webhook_secret="",
        github_token="",
        llm_provider_id="openai-compat",
        llm_base_url="https://api.openai.com/v1",
        llm_api_token="",
        llm_model="gpt-4o",
    )
    with pytest.raises(NotImplementedError):
        build_providers(runtime)


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
    from coreview_shared.runtime.docker import client as docker_client

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
