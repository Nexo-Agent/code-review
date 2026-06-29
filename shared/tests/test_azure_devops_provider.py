import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coreview_shared.git.azure_devops import (
    AzureDevOpsProvider,
    parse_repo_full_name,
)
from coreview_shared.protocols import (
    InlineComment,
    PreparedWorkspace,
    PRMetadata,
    Workspace,
    WorkspaceSpec,
)


def test_parse_repo_full_name_three_segments() -> None:
    assert parse_repo_full_name("fabrikam/MyProject/Repo") == (
        "fabrikam",
        "MyProject",
        "Repo",
    )


def test_parse_repo_full_name_with_defaults() -> None:
    assert parse_repo_full_name(
        "Repo",
        organization="fabrikam",
        project="MyProject",
    ) == ("fabrikam", "MyProject", "Repo")


def test_ado_webhook_basic_auth_valid() -> None:
    secret = "hook-user:hook-pass"
    token = base64.b64encode(b"hook-user:hook-pass").decode()
    provider = AzureDevOpsProvider(pat="")
    assert provider.verify_webhook_signature(b"{}", f"Basic {token}", secret)


def test_ado_webhook_basic_auth_invalid() -> None:
    provider = AzureDevOpsProvider(pat="")
    assert not provider.verify_webhook_signature(b"{}", "Basic abc", "user:pass")
    assert not provider.verify_webhook_signature(b"{}", None, "user:pass")
    assert not provider.verify_webhook_signature(b"{}", "Basic abc", "")


def test_ado_parse_webhook_valid() -> None:
    provider = AzureDevOpsProvider(pat="")
    body = json.dumps(
        {
            "id": "delivery-1",
            "eventType": "git.pullrequest.created",
            "resource": {
                "repository": {
                    "id": "repo-guid",
                    "name": "Fabrikam",
                    "project": {"name": "MyProject"},
                },
                "pullRequestId": 42,
                "status": "active",
                "lastMergeSourceCommit": {"commitId": "abc123"},
            },
            "resourceContainers": {
                "account": {"baseUrl": "https://dev.azure.com/fabrikam/"}
            },
        }
    ).encode()
    event = provider.parse_webhook({}, body)
    assert event is not None
    assert event.repo_full_name == "fabrikam/MyProject/Fabrikam"
    assert event.pr_number == 42
    assert event.head_sha == "abc123"
    assert event.delivery_id == "delivery-1"


def test_ado_build_pr_url() -> None:
    provider = AzureDevOpsProvider(pat="")
    assert provider.build_pr_url("fabrikam/MyProject/Fabrikam", 42) == (
        "https://dev.azure.com/fabrikam/MyProject/_git/Fabrikam/pullrequest/42"
    )


def test_ado_build_blob_url_returns_none() -> None:
    provider = AzureDevOpsProvider(pat="")
    url = provider.build_blob_url("fabrikam/MyProject/Fabrikam", "abc", "a.py", 1)
    assert url is None


def test_ado_parse_webhook_builds_pr_url() -> None:
    provider = AzureDevOpsProvider(pat="")
    body = json.dumps(
        {
            "id": "delivery-1",
            "eventType": "git.pullrequest.created",
            "resource": {
                "repository": {
                    "id": "repo-guid",
                    "name": "Fabrikam",
                    "project": {"name": "MyProject"},
                },
                "pullRequestId": 42,
                "status": "active",
                "lastMergeSourceCommit": {"commitId": "abc123"},
            },
            "resourceContainers": {
                "account": {"baseUrl": "https://dev.azure.com/fabrikam/"}
            },
        }
    ).encode()
    event = provider.parse_webhook({}, body)
    assert event is not None
    assert event.pr_url == (
        "https://dev.azure.com/fabrikam/MyProject/_git/Fabrikam/pullrequest/42"
    )


def test_ado_parse_webhook_ignores_completed() -> None:
    provider = AzureDevOpsProvider(pat="")
    body = json.dumps(
        {
            "eventType": "git.pullrequest.updated",
            "resource": {
                "repository": {
                    "name": "Fabrikam",
                    "project": {"name": "MyProject"},
                },
                "pullRequestId": 1,
                "status": "completed",
                "lastMergeSourceCommit": {"commitId": "abc"},
            },
            "resourceContainers": {
                "account": {"baseUrl": "https://dev.azure.com/fabrikam/"}
            },
        }
    ).encode()
    assert provider.parse_webhook({}, body) is None


@pytest.mark.asyncio
async def test_ado_get_pr_metadata() -> None:
    provider = AzureDevOpsProvider(
        pat="pat",
        organization="fabrikam",
        project="MyProject",
    )
    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "title": "My PR",
                "createdBy": {"displayName": "Alice"},
                "lastMergeSourceCommit": {"commitId": "head-sha"},
                "lastMergeTargetCommit": {"commitId": "base-sha"},
                "sourceRefName": "refs/heads/feature",
                "targetRefName": "refs/heads/main",
                "url": "https://dev.azure.com/fabrikam/pull/1",
                "repository": {"id": "repo-guid"},
            },
        )
        client.get.return_value.raise_for_status = MagicMock()
        client_cls.return_value = client

        metadata = await provider.get_pr_metadata("fabrikam/MyProject/Repo", 1)

    assert metadata.title == "My PR"
    assert metadata.author == "Alice"
    assert metadata.head_sha == "head-sha"
    assert metadata.base_sha == "base-sha"
    assert metadata.head_ref == "feature"
    assert metadata.base_ref == "main"


@pytest.mark.asyncio
async def test_ado_ensure_worktree() -> None:
    provider = AzureDevOpsProvider(pat="pat")
    runner = AsyncMock()
    spec = WorkspaceSpec(
        review_id="r1",
        repo_full_name="fabrikam/MyProject/Repo",
        pr_number=1,
        head_sha="deadbeef0123456789deadbeef0123456789",
    )
    repo_base = Path("/workspaces/azure-devops/fabrikam__myproject__repo")
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
    assert list(access.auth_args) == provider._git_auth_args()


@pytest.mark.asyncio
async def test_ado_prepare_review_uses_local_diff() -> None:
    provider = AzureDevOpsProvider(pat="pat")
    runner = AsyncMock()
    spec = WorkspaceSpec(
        review_id="r1",
        repo_full_name="fabrikam/MyProject/Repo",
        pr_number=1,
        head_sha="head-sha",
    )
    repo_base = Path("/workspaces/azure-devops/fabrikam__myproject__repo")
    prepared_workspace = PreparedWorkspace(
        repo_base=repo_base,
        mirror_path=repo_base / "mirror.git",
        worktree_path=repo_base / "worktrees" / "pr-1-headsha",
        workspace=Workspace(
            path=repo_base / "worktrees" / "pr-1-headsha",
            spec=spec,
        ),
    )
    metadata = PRMetadata(
        repo_full_name="fabrikam/MyProject/Repo",
        pr_number=1,
        title="My PR",
        author="Alice",
        head_sha="head-sha",
        base_sha="base-sha",
        head_ref="feature",
        base_ref="main",
        html_url="https://dev.azure.com/fabrikam/pull/1",
    )

    with (
        patch.object(
            provider,
            "get_pr_metadata",
            new=AsyncMock(return_value=metadata),
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
async def test_ado_post_review_comment() -> None:
    provider = AzureDevOpsProvider(pat="pat")
    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "repo-guid"},
        )
        client.get.return_value.raise_for_status = MagicMock()
        client.post.return_value = MagicMock(status_code=200)
        client.post.return_value.raise_for_status = MagicMock()
        client_cls.return_value = client

        await provider.post_review_comment("fabrikam/MyProject/Repo", 1, "Summary")

        client.post.assert_awaited_once()
        assert "threads" in client.post.await_args.args[0]


@pytest.mark.asyncio
async def test_ado_post_inline_comments_stub() -> None:
    provider = AzureDevOpsProvider(pat="pat")
    comments = [InlineComment(path="a.py", line=1, body="issue")]
    result = await provider.post_inline_comments(
        "fabrikam/MyProject/Repo",
        1,
        "sha",
        comments,
    )
    assert result.posted == ()
    assert result.skipped == tuple(comments)


@pytest.mark.asyncio
async def test_ado_build_diff_from_workspace(tmp_path: Path) -> None:
    provider = AzureDevOpsProvider(pat="pat")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    with patch("asyncio.to_thread", new=AsyncMock(return_value="diff text")):
        diff = await provider.build_diff_from_workspace(
            AsyncMock(),
            repo_path,
            "base",
            "head",
        )
    assert diff == "diff text"
