from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.repo_integrations import RepoIntegrationRow
from app.repositories.review_analytics import ReviewCommentArtifactRow
from app.repositories.teams import DEFAULT_TEAM_ID
from app.services.review_analytics_events import (
    analytics_provider_ids,
    ingest_provider_analytics_event,
    normalize_feedback_keyword,
    normalize_resolution_feedback_keyword,
    supports_applied_fixed_metric,
    supports_review_analytics,
)


def _integration(git_provider: str) -> RepoIntegrationRow:
    now = datetime.now(UTC)
    return RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="acme/backend",
        git_provider=git_provider,
        repo_full_name="acme/backend",
        llm_provider_id=None,
        github_webhook_secret="",
        github_token="",
        system_prompt="",
        enabled=True,
        ado_organization="fabrikam",
        ado_project="MyProject",
        ado_pat="",
        ado_webhook_username="",
        ado_webhook_password="",
        gitlab_base_url="https://gitlab.example.com",
        gitlab_token="",
        gitlab_webhook_secret="",
        bitbucket_token="",
        bitbucket_webhook_secret="",
        bitbucket_dc_base_url="",
        bitbucket_dc_token="",
        bitbucket_dc_webhook_username="",
        bitbucket_dc_webhook_password="",
        created_at=now,
        updated_at=now,
    )


def _artifact_row() -> ReviewCommentArtifactRow:
    now = datetime.now(UTC)
    return ReviewCommentArtifactRow(
        id=uuid4(),
        review_id=uuid4(),
        review_finding_id=None,
        provider="gitlab",
        repo_full_name="acme/backend",
        pr_number=16,
        comment_kind="inline",
        remote_comment_id="100",
        remote_thread_id="disc-1",
        file_path="a.py",
        line_start=10,
        side="RIGHT",
        posted_at=now,
        created_at=now,
    )


def test_supports_review_analytics_for_all_providers() -> None:
    assert supports_review_analytics("github")
    assert supports_review_analytics("gitlab")
    assert supports_review_analytics("azure-devops")
    assert not supports_review_analytics("unknown")


def test_supports_applied_fixed_metric_excludes_ado() -> None:
    assert supports_applied_fixed_metric("github")
    assert supports_applied_fixed_metric("gitlab")
    assert not supports_applied_fixed_metric("azure-devops")


def test_analytics_provider_ids_lists_supported_providers() -> None:
    assert "github" in analytics_provider_ids()
    assert "azure-devops" in analytics_provider_ids()


def test_normalize_feedback_keyword_accepts_quality_keywords() -> None:
    assert normalize_feedback_keyword("Helpful") == {
        "feedback_group": "quality_feedback",
        "feedback_value": "helpful",
        "match_type": "exact_keyword",
    }
    assert normalize_feedback_keyword("Not Helpful.") == {
        "feedback_group": "quality_feedback",
        "feedback_value": "not_helpful",
        "match_type": "exact_keyword",
    }


def test_normalize_feedback_keyword_rejects_resolution_keywords() -> None:
    assert normalize_feedback_keyword("Applied!") is None
    assert normalize_feedback_keyword("this is fixed now") is None


def test_normalize_resolution_feedback_keyword() -> None:
    assert normalize_resolution_feedback_keyword("Applied!") == {
        "feedback_group": "resolution_feedback",
        "feedback_value": "applied",
        "match_type": "exact_keyword",
    }


@pytest.mark.asyncio
async def test_ingest_gitlab_merge_request_open_event() -> None:
    conn = AsyncMock()
    repo = AsyncMock()
    repo.insert_engagement_event = AsyncMock(return_value=MagicMock())
    integration = _integration("gitlab")
    payload = {
        "object_kind": "merge_request",
        "project": {"path_with_namespace": "acme/backend"},
        "user": {"username": "alice"},
        "object_attributes": {
            "id": 93,
            "iid": 16,
            "action": "open",
            "created_at": "2026-06-30T10:00:00Z",
            "updated_at": "2026-06-30T10:00:00Z",
        },
    }
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.review_analytics_events.ReviewAnalyticsRepository",
            lambda _conn: repo,
        )
        count = await ingest_provider_analytics_event(
            conn,
            repo_integration=integration,
            body=__import__("json").dumps(payload).encode(),
            headers={"X-Gitlab-Event": "Merge Request Hook"},
        )
    assert count == 1
    assert repo.insert_engagement_event.await_args.kwargs["event_type"] == "pr_opened"


@pytest.mark.asyncio
async def test_ingest_gitlab_note_reply_records_feedback() -> None:
    conn = AsyncMock()
    repo = AsyncMock()
    artifact = _artifact_row()
    repo.get_comment_artifact_by_remote_thread = AsyncMock(return_value=artifact)
    repo.get_comment_artifact_by_remote_comment = AsyncMock(return_value=None)
    repo.insert_engagement_event = AsyncMock(return_value=MagicMock())
    integration = _integration("gitlab")
    payload = {
        "object_kind": "note",
        "project": {"path_with_namespace": "acme/backend"},
        "user": {"username": "alice"},
        "merge_request": {"iid": 16},
        "discussion": {"id": "disc-1"},
        "object_attributes": {
            "id": 200,
            "noteable_type": "MergeRequest",
            "action": "create",
            "system": False,
            "note": "Helpful",
            "created_at": "2026-06-30T11:00:00Z",
        },
    }
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.review_analytics_events.ReviewAnalyticsRepository",
            lambda _conn: repo,
        )
        count = await ingest_provider_analytics_event(
            conn,
            repo_integration=integration,
            body=__import__("json").dumps(payload).encode(),
            headers={"X-Gitlab-Event": "Note Hook"},
        )
    assert count == 2


@pytest.mark.asyncio
async def test_ingest_bitbucket_cloud_comment_reply() -> None:
    conn = AsyncMock()
    repo = AsyncMock()
    artifact = replace(_artifact_row(), provider="bitbucket", remote_thread_id=None)
    repo.get_comment_artifact_by_remote_comment = AsyncMock(return_value=artifact)
    repo.insert_engagement_event = AsyncMock(return_value=MagicMock())
    integration = _integration("bitbucket")
    payload = {
        "repository": {"full_name": "acme/backend"},
        "actor": {"nickname": "alice"},
        "pullrequest": {"id": 16},
        "comment": {
            "id": 55,
            "parent": {"id": 100},
            "content": {"raw": "Not Helpful"},
            "created_on": "2026-06-30T11:00:00Z",
        },
    }
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.review_analytics_events.ReviewAnalyticsRepository",
            lambda _conn: repo,
        )
        count = await ingest_provider_analytics_event(
            conn,
            repo_integration=integration,
            body=__import__("json").dumps(payload).encode(),
            headers={"X-Event-Key": "pullrequest:comment_created"},
        )
    assert count == 2


@pytest.mark.asyncio
async def test_ingest_ado_comment_reply_without_resolution_feedback() -> None:
    conn = AsyncMock()
    repo = AsyncMock()
    artifact = replace(
        _artifact_row(),
        provider="azure-devops",
        remote_thread_id="9",
    )
    repo.get_comment_artifact_by_remote_comment = AsyncMock(return_value=artifact)
    repo.insert_engagement_event = AsyncMock(return_value=MagicMock())
    integration = _integration("azure-devops")
    payload = {
        "id": str(uuid4()),
        "eventType": "git.pullrequest.commented.on",
        "resource": {
            "pullRequestId": 16,
            "repository": {
                "name": "backend",
                "project": {"name": "MyProject"},
            },
            "comment": {
                "id": 3,
                "parentCommentId": 100,
                "content": "Fixed",
                "publishedDate": "2026-06-30T11:00:00Z",
                "author": {"uniqueName": "alice@example.com"},
            },
        },
        "resourceContainers": {
            "account": {"baseUrl": "https://dev.azure.com/fabrikam/"}
        },
    }
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.review_analytics_events.ReviewAnalyticsRepository",
            lambda _conn: repo,
        )
        count = await ingest_provider_analytics_event(
            conn,
            repo_integration=integration,
            body=__import__("json").dumps(payload).encode(),
            headers={},
        )
    assert count == 1
    assert all(
        call.kwargs.get("event_type") != "feedback_classified"
        for call in repo.insert_engagement_event.await_args_list
    )
