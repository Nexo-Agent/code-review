from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from uuid import UUID

from app.repositories.repo_integrations import RepoIntegrationRow
from app.repositories.review_analytics import (
    ReviewAnalyticsRepository,
    ReviewCommentArtifactRow,
)
from app.repositories.reviews import ReviewRow

_QUALITY_FEEDBACK_KEYWORDS: dict[str, tuple[str, str]] = {
    "helpful": ("quality_feedback", "helpful"),
    "not helpful": ("quality_feedback", "not_helpful"),
}
_RESOLUTION_FEEDBACK_KEYWORDS: dict[str, tuple[str, str]] = {
    "fixed": ("resolution_feedback", "fixed"),
    "applied": ("resolution_feedback", "applied"),
    "dismissed": ("resolution_feedback", "dismissed"),
    "deferred": ("resolution_feedback", "deferred"),
}
_FEEDBACK_KEYWORDS: dict[str, tuple[str, str]] = {
    **_QUALITY_FEEDBACK_KEYWORDS,
    **_RESOLUTION_FEEDBACK_KEYWORDS,
}
_TRAILING_PUNCTUATION_RE = re.compile(r"[.!?]+$")

_ANALYTICS_PROVIDERS = frozenset(
    {"github", "gitlab", "azure-devops", "bitbucket", "bitbucket-dc"}
)
_APPLIED_FIXED_PROVIDERS = frozenset({"github", "gitlab", "bitbucket", "bitbucket-dc"})


def analytics_provider_ids() -> tuple[str, ...]:
    return tuple(sorted(_ANALYTICS_PROVIDERS))


def supports_review_analytics(git_provider: str) -> bool:
    return git_provider in _ANALYTICS_PROVIDERS


def supports_applied_fixed_metric(git_provider: str) -> bool:
    return git_provider in _APPLIED_FIXED_PROVIDERS


def normalize_feedback_keyword(body: str) -> dict[str, str] | None:
    normalized = _TRAILING_PUNCTUATION_RE.sub("", body.strip().lower())
    classification = _QUALITY_FEEDBACK_KEYWORDS.get(normalized)
    if classification is None:
        return None
    return {
        "feedback_group": classification[0],
        "feedback_value": classification[1],
        "match_type": "exact_keyword",
    }


def normalize_resolution_feedback_keyword(body: str) -> dict[str, str] | None:
    normalized = _TRAILING_PUNCTUATION_RE.sub("", body.strip().lower())
    classification = _RESOLUTION_FEEDBACK_KEYWORDS.get(normalized)
    if classification is None:
        return None
    return {
        "feedback_group": classification[0],
        "feedback_value": classification[1],
        "match_type": "exact_keyword",
    }


async def persist_comment_artifacts_and_events(
    conn,
    *,
    review: ReviewRow,
    repo_integration: RepoIntegrationRow | None,
    artifacts: list[dict[str, object]],
    finding_ids_by_index: dict[int, UUID],
) -> list[ReviewCommentArtifactRow]:
    if not artifacts:
        return []
    repo = ReviewAnalyticsRepository(conn)
    rows = await repo.replace_comment_artifacts(
        review_id=review.id,
        provider=review.provider,
        repo_full_name=review.repo_full_name,
        pr_number=review.pr_number,
        artifacts=artifacts,
        finding_ids_by_index=finding_ids_by_index,
    )
    for row in rows:
        repo_integration_id = (
            repo_integration.id if repo_integration else review.repo_integration_id
        )
        await repo.insert_engagement_event(
            provider=row.provider,
            repo_full_name=row.repo_full_name,
            pr_number=row.pr_number,
            review_id=row.review_id,
            review_finding_id=row.review_finding_id,
            comment_artifact_id=row.id,
            repo_integration_id=repo_integration_id,
            team_id=review.team_id,
            event_family="ai_comment",
            event_type="ai_comment_posted",
            event_at=row.posted_at,
            actor_login="cogito-review",
            actor_type="system",
            provider_delivery_id=str(review.id),
            provider_event_id="agent_callback",
            provider_object_id=row.remote_comment_id,
            dedup_key=(
                f"{row.provider}:ai_comment_posted:{review.id}:{row.remote_comment_id}"
            ),
            payload_json={
                "comment_kind": row.comment_kind,
                "remote_comment_id": row.remote_comment_id,
                "remote_thread_id": row.remote_thread_id,
            },
            normalized_json={
                "comment_kind": row.comment_kind,
                "review_finding_id": (
                    str(row.review_finding_id) if row.review_finding_id else None
                ),
                "file_path": row.file_path,
                "line_start": row.line_start,
            },
        )
    return rows


async def ingest_provider_analytics_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    body: bytes,
    headers: dict[str, str],
) -> int:
    if not supports_review_analytics(repo_integration.git_provider):
        msg = f"Review analytics not implemented for {repo_integration.git_provider}"
        raise NotImplementedError(msg)
    provider = repo_integration.git_provider
    if provider == "github":
        return await _ingest_github_analytics_event(
            conn,
            repo_integration=repo_integration,
            body=body,
            headers=headers,
        )
    if provider == "gitlab":
        return await _ingest_gitlab_analytics_event(
            conn,
            repo_integration=repo_integration,
            body=body,
            headers=headers,
        )
    if provider == "bitbucket":
        return await _ingest_bitbucket_cloud_analytics_event(
            conn,
            repo_integration=repo_integration,
            body=body,
            headers=headers,
        )
    if provider == "bitbucket-dc":
        return await _ingest_bitbucket_dc_analytics_event(
            conn,
            repo_integration=repo_integration,
            body=body,
            headers=headers,
        )
    if provider == "azure-devops":
        return await _ingest_ado_analytics_event(
            conn,
            repo_integration=repo_integration,
            body=body,
            headers=headers,
        )
    return 0


async def _record_human_reply(
    conn,
    *,
    provider: str,
    repo_integration: RepoIntegrationRow,
    repo_full_name: str,
    pr_number: int,
    artifact: ReviewCommentArtifactRow,
    event_at: datetime,
    actor_login: str,
    body: str,
    provider_delivery_id: str,
    provider_event_id: str,
    provider_object_id: str,
    payload: dict,
    dedup_prefix: str,
    include_resolution_feedback: bool,
) -> int:
    repo = ReviewAnalyticsRepository(conn)
    inserted = 0
    raw_event = await repo.insert_engagement_event(
        provider=provider,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        review_id=artifact.review_id,
        review_finding_id=artifact.review_finding_id,
        comment_artifact_id=artifact.id,
        repo_integration_id=repo_integration.id,
        team_id=repo_integration.team_id,
        event_family="human_reply",
        event_type="human_replied",
        event_at=event_at,
        actor_login=actor_login,
        actor_type="human",
        provider_delivery_id=provider_delivery_id,
        provider_event_id=provider_event_id,
        provider_object_id=provider_object_id,
        dedup_key=f"{dedup_prefix}:human_replied:{provider_object_id}",
        payload_json=payload,
        normalized_json={
            "parent_remote_comment_id": artifact.remote_comment_id,
            "body": body,
        },
    )
    if raw_event is not None:
        inserted += 1
    feedback = normalize_feedback_keyword(body)
    if feedback is None and include_resolution_feedback:
        feedback = normalize_resolution_feedback_keyword(body)
    if feedback is None:
        return inserted
    classified = await repo.insert_engagement_event(
        provider=provider,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        review_id=artifact.review_id,
        review_finding_id=artifact.review_finding_id,
        comment_artifact_id=artifact.id,
        repo_integration_id=repo_integration.id,
        team_id=repo_integration.team_id,
        event_family="feedback_classified",
        event_type="feedback_classified",
        event_at=event_at,
        actor_login=actor_login,
        actor_type="human",
        provider_delivery_id=provider_delivery_id,
        provider_event_id=provider_event_id,
        provider_object_id=provider_object_id,
        dedup_key=f"{dedup_prefix}:feedback_classified:{provider_object_id}",
        payload_json=payload,
        normalized_json=feedback,
    )
    if classified is not None:
        inserted += 1
    return inserted


async def _ingest_github_analytics_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    body: bytes,
    headers: dict[str, str],
) -> int:
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    event_type = normalized_headers.get("x-github-event", "")
    delivery_id = normalized_headers.get("x-github-delivery", "")
    payload = json.loads(body)
    if event_type == "pull_request":
        return await _ingest_github_pull_request_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            delivery_id=delivery_id,
        )
    if event_type == "pull_request_review_comment":
        return await _ingest_github_review_comment_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            delivery_id=delivery_id,
        )
    return 0


async def _ingest_github_pull_request_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    delivery_id: str,
) -> int:
    action = str(payload.get("action") or "")
    pr = payload.get("pull_request")
    repo = payload.get("repository")
    sender = payload.get("sender")
    if not isinstance(pr, dict) or not isinstance(repo, dict):
        return 0
    pr_number = int(pr.get("number") or 0)
    if pr_number < 1:
        return 0
    event_type = _map_github_pull_request_event_type(action, pr)
    if event_type is None:
        return 0
    event_at = _github_pull_request_event_time(event_type, pr)
    repo_db = ReviewAnalyticsRepository(conn)
    inserted = await repo_db.insert_engagement_event(
        provider="github",
        repo_full_name=str(repo.get("full_name") or repo_integration.repo_full_name),
        pr_number=pr_number,
        review_id=None,
        review_finding_id=None,
        comment_artifact_id=None,
        repo_integration_id=repo_integration.id,
        team_id=repo_integration.team_id,
        event_family="pr_lifecycle",
        event_type=event_type,
        event_at=event_at,
        actor_login=_github_actor_login(sender),
        actor_type=_github_actor_type(sender),
        provider_delivery_id=delivery_id,
        provider_event_id=action,
        provider_object_id=str(pr.get("id") or pr_number),
        dedup_key=f"github:{delivery_id}:{event_type}:{pr_number}",
        payload_json=payload,
        normalized_json={
            "action": action,
            "draft": bool(pr.get("draft", False)),
            "merged": bool(pr.get("merged", False)),
        },
    )
    return 1 if inserted is not None else 0


async def _ingest_github_review_comment_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    delivery_id: str,
) -> int:
    if str(payload.get("action") or "") != "created":
        return 0
    comment = payload.get("comment")
    pull_request = payload.get("pull_request")
    repository = payload.get("repository")
    sender = payload.get("sender")
    if not isinstance(comment, dict) or not isinstance(pull_request, dict):
        return 0
    if _github_actor_type(sender) != "human":
        return 0
    parent_id = comment.get("in_reply_to_id")
    if parent_id is None:
        return 0
    repo_full_name = str(
        (repository or {}).get("full_name") or repo_integration.repo_full_name
    )
    pr_number = int(pull_request.get("number") or 0)
    repo = ReviewAnalyticsRepository(conn)
    artifact = await repo.get_comment_artifact_by_remote_comment(
        provider="github",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        remote_comment_id=str(parent_id),
    )
    if artifact is None:
        return 0
    return await _record_human_reply(
        conn,
        provider="github",
        repo_integration=repo_integration,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        artifact=artifact,
        event_at=_parse_timestamp(str(comment.get("created_at") or "")),
        actor_login=_github_actor_login(sender),
        body=str(comment.get("body") or ""),
        provider_delivery_id=delivery_id,
        provider_event_id="created",
        provider_object_id=str(comment.get("id") or ""),
        payload=payload,
        dedup_prefix=f"github:{delivery_id}",
        include_resolution_feedback=True,
    )


async def _ingest_gitlab_analytics_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    body: bytes,
    headers: dict[str, str],
) -> int:
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    delivery_id = (
        normalized_headers.get("x-gitlab-event-uuid")
        or normalized_headers.get("x-gitlab-delivery")
        or normalized_headers.get("webhook-id")
        or ""
    )
    payload = json.loads(body)
    object_kind = str(payload.get("object_kind") or "")
    if object_kind == "merge_request":
        return await _ingest_gitlab_merge_request_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            delivery_id=delivery_id,
        )
    if object_kind == "note":
        return await _ingest_gitlab_note_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            delivery_id=delivery_id,
        )
    return 0


async def _ingest_gitlab_merge_request_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    delivery_id: str,
) -> int:
    object_attributes = payload.get("object_attributes")
    project = payload.get("project")
    user = payload.get("user")
    if not isinstance(object_attributes, dict) or not isinstance(project, dict):
        return 0
    pr_number = int(object_attributes.get("iid") or 0)
    if pr_number < 1:
        return 0
    action = str(object_attributes.get("action") or "")
    event_type = _map_gitlab_merge_request_event_type(
        action, object_attributes, payload
    )
    if event_type is None:
        return 0
    event_at = _gitlab_merge_request_event_time(event_type, object_attributes)
    repo_full_name = str(
        project.get("path_with_namespace") or repo_integration.repo_full_name
    )
    repo_db = ReviewAnalyticsRepository(conn)
    inserted = await repo_db.insert_engagement_event(
        provider="gitlab",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        review_id=None,
        review_finding_id=None,
        comment_artifact_id=None,
        repo_integration_id=repo_integration.id,
        team_id=repo_integration.team_id,
        event_family="pr_lifecycle",
        event_type=event_type,
        event_at=event_at,
        actor_login=_gitlab_actor_login(user),
        actor_type=_gitlab_actor_type(user),
        provider_delivery_id=delivery_id,
        provider_event_id=action,
        provider_object_id=str(object_attributes.get("id") or pr_number),
        dedup_key=f"gitlab:{delivery_id}:{event_type}:{pr_number}",
        payload_json=payload,
        normalized_json={
            "action": action,
            "draft": bool(object_attributes.get("draft", False)),
        },
    )
    return 1 if inserted is not None else 0


async def _ingest_gitlab_note_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    delivery_id: str,
) -> int:
    object_attributes = payload.get("object_attributes")
    merge_request = payload.get("merge_request")
    project = payload.get("project")
    user = payload.get("user")
    if not isinstance(object_attributes, dict):
        return 0
    if str(object_attributes.get("noteable_type") or "") != "MergeRequest":
        return 0
    if str(object_attributes.get("action") or "") != "create":
        return 0
    if bool(object_attributes.get("system", False)):
        return 0
    if _gitlab_actor_type(user) != "human":
        return 0
    if not isinstance(merge_request, dict):
        return 0
    pr_number = int(merge_request.get("iid") or 0)
    if pr_number < 1:
        return 0
    repo_full_name = str(
        (project or {}).get("path_with_namespace") or repo_integration.repo_full_name
    )
    note_id = str(object_attributes.get("id") or "")
    body = str(object_attributes.get("note") or "")
    repo = ReviewAnalyticsRepository(conn)
    artifact = await _resolve_gitlab_reply_artifact(
        repo,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        object_attributes=object_attributes,
        payload=payload,
        note_id=note_id,
    )
    if artifact is None:
        return 0
    if note_id == artifact.remote_comment_id:
        return 0
    return await _record_human_reply(
        conn,
        provider="gitlab",
        repo_integration=repo_integration,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        artifact=artifact,
        event_at=_parse_timestamp(str(object_attributes.get("created_at") or "")),
        actor_login=_gitlab_actor_login(user),
        body=body,
        provider_delivery_id=delivery_id,
        provider_event_id="create",
        provider_object_id=note_id,
        payload=payload,
        dedup_prefix=f"gitlab:{delivery_id}",
        include_resolution_feedback=supports_applied_fixed_metric("gitlab"),
    )


async def _resolve_gitlab_reply_artifact(
    repo: ReviewAnalyticsRepository,
    *,
    repo_full_name: str,
    pr_number: int,
    object_attributes: dict,
    payload: dict,
    note_id: str,
) -> ReviewCommentArtifactRow | None:
    in_reply_to = object_attributes.get("in_reply_to_id")
    if in_reply_to is not None:
        artifact = await repo.get_comment_artifact_by_remote_comment(
            provider="gitlab",
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            remote_comment_id=str(in_reply_to),
        )
        if artifact is not None:
            return artifact
    discussion_id = _gitlab_discussion_id(object_attributes, payload)
    if discussion_id:
        artifact = await repo.get_comment_artifact_by_remote_thread(
            provider="gitlab",
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            remote_thread_id=discussion_id,
        )
        if artifact is not None and note_id != artifact.remote_comment_id:
            return artifact
    return None


async def _ingest_bitbucket_cloud_analytics_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    body: bytes,
    headers: dict[str, str],
) -> int:
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    event_key = normalized_headers.get("x-event-key", "")
    delivery_id = (
        normalized_headers.get("x-hook-uuid")
        or normalized_headers.get("x-request-uuid")
        or ""
    )
    payload = json.loads(body)
    if event_key == "pullrequest:comment_created":
        return await _ingest_bitbucket_cloud_comment_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            delivery_id=delivery_id,
        )
    if event_key in {
        "pullrequest:created",
        "pullrequest:updated",
        "pullrequest:fulfilled",
    }:
        return await _ingest_bitbucket_cloud_lifecycle_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            event_key=event_key,
            delivery_id=delivery_id,
        )
    return 0


async def _ingest_bitbucket_cloud_lifecycle_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    event_key: str,
    delivery_id: str,
) -> int:
    pullrequest = payload.get("pullrequest")
    repository = payload.get("repository")
    actor = payload.get("actor")
    if not isinstance(pullrequest, dict) or not isinstance(repository, dict):
        return 0
    pr_number = int(pullrequest.get("id") or 0)
    if pr_number < 1:
        return 0
    event_type = _map_bitbucket_cloud_lifecycle_event_type(
        event_key,
        pullrequest,
        payload,
    )
    if event_type is None:
        return 0
    repo_full_name = str(repository.get("full_name") or repo_integration.repo_full_name)
    event_at = _parse_timestamp(
        str(pullrequest.get("updated_on") or pullrequest.get("created_on") or "")
    )
    repo_db = ReviewAnalyticsRepository(conn)
    inserted = await repo_db.insert_engagement_event(
        provider="bitbucket",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        review_id=None,
        review_finding_id=None,
        comment_artifact_id=None,
        repo_integration_id=repo_integration.id,
        team_id=repo_integration.team_id,
        event_family="pr_lifecycle",
        event_type=event_type,
        event_at=event_at,
        actor_login=_bitbucket_actor_login(actor),
        actor_type=_bitbucket_actor_type(actor),
        provider_delivery_id=delivery_id,
        provider_event_id=event_key,
        provider_object_id=str(pr_number),
        dedup_key=f"bitbucket:{delivery_id}:{event_type}:{pr_number}",
        payload_json=payload,
        normalized_json={"event_key": event_key},
    )
    return 1 if inserted is not None else 0


async def _ingest_bitbucket_cloud_comment_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    delivery_id: str,
) -> int:
    comment = payload.get("comment")
    pullrequest = payload.get("pullrequest")
    repository = payload.get("repository")
    actor = payload.get("actor")
    if not isinstance(comment, dict) or not isinstance(pullrequest, dict):
        return 0
    if _bitbucket_actor_type(actor) != "human":
        return 0
    parent = comment.get("parent")
    if not isinstance(parent, dict):
        return 0
    parent_id = parent.get("id")
    if parent_id is None:
        return 0
    pr_number = int(pullrequest.get("id") or 0)
    if pr_number < 1:
        return 0
    repo_full_name = str(
        (repository or {}).get("full_name") or repo_integration.repo_full_name
    )
    repo = ReviewAnalyticsRepository(conn)
    artifact = await repo.get_comment_artifact_by_remote_comment(
        provider="bitbucket",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        remote_comment_id=str(parent_id),
    )
    if artifact is None:
        return 0
    content = comment.get("content")
    body = ""
    if isinstance(content, dict):
        body = str(content.get("raw") or "")
    return await _record_human_reply(
        conn,
        provider="bitbucket",
        repo_integration=repo_integration,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        artifact=artifact,
        event_at=_parse_timestamp(str(comment.get("created_on") or "")),
        actor_login=_bitbucket_actor_login(actor),
        body=body,
        provider_delivery_id=delivery_id,
        provider_event_id="comment_created",
        provider_object_id=str(comment.get("id") or ""),
        payload=payload,
        dedup_prefix=f"bitbucket:{delivery_id}",
        include_resolution_feedback=supports_applied_fixed_metric("bitbucket"),
    )


async def _ingest_bitbucket_dc_analytics_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    body: bytes,
    headers: dict[str, str],
) -> int:
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    event_key = normalized_headers.get("x-event-key", "")
    delivery_id = normalized_headers.get("x-request-id") or ""
    payload = json.loads(body)
    if event_key in {"pr:comment:added", "pr:comment_added"}:
        return await _ingest_bitbucket_dc_comment_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            delivery_id=delivery_id,
        )
    if event_key in {"pr:opened", "pr:reopened", "pr:merged", "pr:modified"}:
        return await _ingest_bitbucket_dc_lifecycle_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            event_key=event_key,
            delivery_id=delivery_id,
        )
    return 0


async def _ingest_bitbucket_dc_lifecycle_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    event_key: str,
    delivery_id: str,
) -> int:
    pull_request = payload.get("pullRequest")
    actor = payload.get("actor")
    if not isinstance(pull_request, dict):
        return 0
    pr_number = int(pull_request.get("id") or 0)
    if pr_number < 1:
        return 0
    repo_full_name = _bitbucket_dc_repo_full_name(pull_request, repo_integration)
    if not repo_full_name:
        return 0
    event_type = _map_bitbucket_dc_lifecycle_event_type(event_key, pull_request)
    if event_type is None:
        return 0
    event_at = _parse_timestamp(
        str(pull_request.get("updatedDate") or pull_request.get("createdDate") or "")
    )
    repo_db = ReviewAnalyticsRepository(conn)
    inserted = await repo_db.insert_engagement_event(
        provider="bitbucket-dc",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        review_id=None,
        review_finding_id=None,
        comment_artifact_id=None,
        repo_integration_id=repo_integration.id,
        team_id=repo_integration.team_id,
        event_family="pr_lifecycle",
        event_type=event_type,
        event_at=event_at,
        actor_login=_bitbucket_dc_actor_login(actor),
        actor_type=_bitbucket_dc_actor_type(actor),
        provider_delivery_id=delivery_id,
        provider_event_id=event_key,
        provider_object_id=str(pr_number),
        dedup_key=f"bitbucket-dc:{delivery_id}:{event_type}:{pr_number}",
        payload_json=payload,
        normalized_json={"event_key": event_key},
    )
    return 1 if inserted is not None else 0


async def _ingest_bitbucket_dc_comment_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    delivery_id: str,
) -> int:
    comment = payload.get("comment")
    pull_request = payload.get("pullRequest")
    actor = payload.get("actor")
    if not isinstance(comment, dict) or not isinstance(pull_request, dict):
        return 0
    if _bitbucket_dc_actor_type(actor) != "human":
        return 0
    parent = comment.get("parent")
    if not isinstance(parent, dict):
        return 0
    parent_id = parent.get("id")
    if parent_id is None:
        return 0
    pr_number = int(pull_request.get("id") or 0)
    if pr_number < 1:
        return 0
    repo_full_name = _bitbucket_dc_repo_full_name(pull_request, repo_integration)
    if not repo_full_name:
        return 0
    repo = ReviewAnalyticsRepository(conn)
    artifact = await repo.get_comment_artifact_by_remote_comment(
        provider="bitbucket-dc",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        remote_comment_id=str(parent_id),
    )
    if artifact is None:
        return 0
    return await _record_human_reply(
        conn,
        provider="bitbucket-dc",
        repo_integration=repo_integration,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        artifact=artifact,
        event_at=_parse_timestamp(str(comment.get("createdDate") or "")),
        actor_login=_bitbucket_dc_actor_login(actor),
        body=str(comment.get("text") or ""),
        provider_delivery_id=delivery_id,
        provider_event_id="comment_added",
        provider_object_id=str(comment.get("id") or ""),
        payload=payload,
        dedup_prefix=f"bitbucket-dc:{delivery_id}",
        include_resolution_feedback=supports_applied_fixed_metric("bitbucket-dc"),
    )


async def _ingest_ado_analytics_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    body: bytes,
    headers: dict[str, str],
) -> int:
    del headers
    payload = json.loads(body)
    event_type = str(payload.get("eventType") or "")
    delivery_id = str(payload.get("id") or "")
    if event_type == "git.pullrequest.commented.on":
        return await _ingest_ado_comment_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            delivery_id=delivery_id,
        )
    if event_type in {"git.pullrequest.created", "git.pullrequest.updated"}:
        return await _ingest_ado_lifecycle_event(
            conn,
            repo_integration=repo_integration,
            payload=payload,
            event_type=event_type,
            delivery_id=delivery_id,
        )
    return 0


async def _ingest_ado_lifecycle_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    event_type: str,
    delivery_id: str,
) -> int:
    resource = payload.get("resource")
    if not isinstance(resource, dict):
        return 0
    repository = resource.get("repository")
    if not isinstance(repository, dict):
        return 0
    pr_number = int(resource.get("pullRequestId") or 0)
    if pr_number < 1:
        return 0
    repo_full_name = _ado_repo_full_name(payload, repository, repo_integration)
    if not repo_full_name:
        return 0
    lifecycle_type = _map_ado_lifecycle_event_type(event_type, resource)
    if lifecycle_type is None:
        return 0
    created_by = resource.get("createdBy")
    event_at = _ado_lifecycle_event_time(lifecycle_type, resource)
    repo_db = ReviewAnalyticsRepository(conn)
    inserted = await repo_db.insert_engagement_event(
        provider="azure-devops",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        review_id=None,
        review_finding_id=None,
        comment_artifact_id=None,
        repo_integration_id=repo_integration.id,
        team_id=repo_integration.team_id,
        event_family="pr_lifecycle",
        event_type=lifecycle_type,
        event_at=event_at,
        actor_login=_ado_actor_login(created_by),
        actor_type=_ado_actor_type(created_by),
        provider_delivery_id=delivery_id,
        provider_event_id=event_type,
        provider_object_id=str(pr_number),
        dedup_key=f"azure-devops:{delivery_id}:{lifecycle_type}:{pr_number}",
        payload_json=payload,
        normalized_json={"event_type": event_type},
    )
    return 1 if inserted is not None else 0


async def _ingest_ado_comment_event(
    conn,
    *,
    repo_integration: RepoIntegrationRow,
    payload: dict,
    delivery_id: str,
) -> int:
    resource = payload.get("resource")
    if not isinstance(resource, dict):
        return 0
    repository = resource.get("repository")
    comment = resource.get("comment")
    if not isinstance(repository, dict) or not isinstance(comment, dict):
        return 0
    parent_comment_id = comment.get("parentCommentId")
    if parent_comment_id in (None, 0):
        return 0
    pr_number = int(resource.get("pullRequestId") or 0)
    if pr_number < 1:
        return 0
    repo_full_name = _ado_repo_full_name(payload, repository, repo_integration)
    if not repo_full_name:
        return 0
    identities = comment.get("author") or resource.get("commentedBy")
    if _ado_actor_type(identities) != "human":
        return 0
    repo = ReviewAnalyticsRepository(conn)
    artifact = await repo.get_comment_artifact_by_remote_comment(
        provider="azure-devops",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        remote_comment_id=str(parent_comment_id),
    )
    if artifact is None:
        return 0
    content = comment.get("content")
    body = str(content) if isinstance(content, str) else ""
    return await _record_human_reply(
        conn,
        provider="azure-devops",
        repo_integration=repo_integration,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        artifact=artifact,
        event_at=_parse_timestamp(str(comment.get("publishedDate") or "")),
        actor_login=_ado_actor_login(identities),
        body=body,
        provider_delivery_id=delivery_id,
        provider_event_id="commented.on",
        provider_object_id=str(comment.get("id") or ""),
        payload=payload,
        dedup_prefix=f"azure-devops:{delivery_id}",
        include_resolution_feedback=False,
    )


def _map_github_pull_request_event_type(
    action: str,
    pull_request: dict,
) -> str | None:
    if action == "opened":
        return "pr_opened"
    if action == "reopened":
        return "pr_reopened"
    if action == "ready_for_review":
        return "pr_ready_for_review"
    if action == "closed" and bool(pull_request.get("merged", False)):
        return "pr_merged"
    return None


def _map_gitlab_merge_request_event_type(
    action: str,
    object_attributes: dict,
    payload: dict,
) -> str | None:
    if action == "open":
        return "pr_opened"
    if action == "reopen":
        return "pr_reopened"
    if action == "merge":
        return "pr_merged"
    if action == "update" and _gitlab_draft_ready_transition(
        object_attributes, payload
    ):
        return "pr_ready_for_review"
    return None


def _map_bitbucket_cloud_lifecycle_event_type(
    event_key: str,
    pullrequest: dict,
    payload: dict,
) -> str | None:
    if event_key == "pullrequest:created":
        return "pr_opened"
    if event_key == "pullrequest:fulfilled":
        return "pr_merged"
    if event_key == "pullrequest:updated" and _bitbucket_draft_ready_transition(
        pullrequest,
        payload,
    ):
        return "pr_ready_for_review"
    return None


def _map_bitbucket_dc_lifecycle_event_type(
    event_key: str,
    pull_request: dict,
) -> str | None:
    if event_key in {"pr:opened", "pr:reopened"}:
        return "pr_opened" if event_key == "pr:opened" else "pr_reopened"
    if event_key == "pr:merged":
        return "pr_merged"
    if event_key == "pr:modified" and not bool(pull_request.get("draft", False)):
        changes = pull_request.get("draft")
        if changes is False:
            return "pr_ready_for_review"
    return None


def _map_ado_lifecycle_event_type(event_type: str, resource: dict) -> str | None:
    status = str(resource.get("status") or "").lower()
    if event_type == "git.pullrequest.created" and status == "active":
        return "pr_opened"
    if event_type == "git.pullrequest.updated":
        if status == "completed" and str(resource.get("mergeStatus") or "").lower() in {
            "succeeded",
            "success",
        }:
            return "pr_merged"
        if resource.get("isDraft") is False and _ado_draft_ready_transition(resource):
            return "pr_ready_for_review"
    return None


def _gitlab_draft_ready_transition(object_attributes: dict, payload: dict) -> bool:
    changes = payload.get("changes")
    if isinstance(changes, dict):
        for key in ("draft", "work_in_progress"):
            change = changes.get(key)
            if isinstance(change, dict):
                previous = change.get("previous")
                current = change.get("current")
                if previous in (True, "true", 1) and current in (False, "false", 0):
                    return True
    draft = object_attributes.get("draft")
    wip = object_attributes.get("work_in_progress")
    return draft is False and wip is False


def _bitbucket_draft_ready_transition(pullrequest: dict, payload: dict) -> bool:
    changes = payload.get("changes")
    if isinstance(changes, dict):
        draft_change = changes.get("draft")
        if isinstance(draft_change, dict):
            old = draft_change.get("old")
            new = draft_change.get("new")
            if old in (True, "true") and new in (False, "false"):
                return True
    return bool(pullrequest.get("draft") is False)


def _ado_draft_ready_transition(resource: dict) -> bool:
    return resource.get("isDraft") is False


def _gitlab_discussion_id(object_attributes: dict, payload: dict) -> str | None:
    discussion = payload.get("discussion")
    if isinstance(discussion, dict) and discussion.get("id") is not None:
        return str(discussion["id"])
    discussion_id = object_attributes.get("discussion_id")
    if discussion_id is not None:
        return str(discussion_id)
    return None


def _bitbucket_dc_repo_full_name(
    pull_request: dict,
    repo_integration: RepoIntegrationRow,
) -> str:
    to_ref = pull_request.get("toRef")
    if not isinstance(to_ref, dict):
        return repo_integration.repo_full_name
    repository = to_ref.get("repository")
    if not isinstance(repository, dict):
        return repo_integration.repo_full_name
    project = repository.get("project")
    project_key = project.get("key", "") if isinstance(project, dict) else ""
    repo_slug = str(repository.get("slug") or "")
    if project_key and repo_slug:
        return f"{project_key}/{repo_slug}"
    return repo_integration.repo_full_name


def _ado_repo_full_name(
    payload: dict,
    repository: dict,
    repo_integration: RepoIntegrationRow,
) -> str:
    project = repository.get("project")
    if not isinstance(project, dict):
        return repo_integration.repo_full_name
    repo_name = str(repository.get("name") or "")
    project_name = str(project.get("name") or "")
    containers = payload.get("resourceContainers", {})
    account = containers.get("account", {})
    base_url = account.get("baseUrl", "") if isinstance(account, dict) else ""
    organization = ""
    if base_url:
        organization = base_url.rstrip("/").split("/")[-1]
    if not organization:
        organization = repo_integration.ado_organization
    if organization and project_name and repo_name:
        return f"{organization}/{project_name}/{repo_name}"
    return repo_integration.repo_full_name


def _github_pull_request_event_time(event_type: str, pull_request: dict) -> datetime:
    if event_type == "pr_opened":
        return _parse_timestamp(str(pull_request.get("created_at") or ""))
    if event_type == "pr_merged":
        merged_at = str(pull_request.get("merged_at") or "")
        if merged_at:
            return _parse_timestamp(merged_at)
    updated_at = str(pull_request.get("updated_at") or "")
    if updated_at:
        return _parse_timestamp(updated_at)
    return datetime.now(tz=UTC)


def _gitlab_merge_request_event_time(
    event_type: str,
    object_attributes: dict,
) -> datetime:
    if event_type == "pr_opened":
        return _parse_timestamp(str(object_attributes.get("created_at") or ""))
    if event_type == "pr_merged":
        return _parse_timestamp(str(object_attributes.get("updated_at") or ""))
    return _parse_timestamp(str(object_attributes.get("updated_at") or ""))


def _ado_lifecycle_event_time(event_type: str, resource: dict) -> datetime:
    if event_type == "pr_opened":
        return _parse_timestamp(str(resource.get("creationDate") or ""))
    if event_type == "pr_merged":
        return _parse_timestamp(str(resource.get("closedDate") or ""))
    return _parse_timestamp(str(resource.get("creationDate") or ""))


def _parse_timestamp(value: str) -> datetime:
    if not value.strip():
        return datetime.now(tz=UTC)
    normalized = value.strip().replace(" UTC", "Z").replace(" ", "T", 1)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized).astimezone(UTC)
    except ValueError:
        return datetime.now(tz=UTC)


def _parse_github_timestamp(value: str) -> datetime:
    return _parse_timestamp(value)


def _github_actor_login(actor: object) -> str:
    if not isinstance(actor, dict):
        return ""
    return str(actor.get("login") or "")


def _github_actor_type(actor: object) -> str:
    if not isinstance(actor, dict):
        return "unknown"
    actor_type = str(actor.get("type") or "").lower()
    if actor_type == "user":
        return "human"
    if actor_type:
        return "bot"
    return "unknown"


def _gitlab_actor_login(actor: object) -> str:
    if not isinstance(actor, dict):
        return ""
    return str(actor.get("username") or actor.get("name") or "")


def _gitlab_actor_type(actor: object) -> str:
    if not isinstance(actor, dict):
        return "unknown"
    if actor.get("bot") is True:
        return "bot"
    return "human"


def _bitbucket_actor_login(actor: object) -> str:
    if not isinstance(actor, dict):
        return ""
    return str(actor.get("nickname") or actor.get("display_name") or "")


def _bitbucket_actor_type(actor: object) -> str:
    if not isinstance(actor, dict):
        return "unknown"
    if actor.get("type") == "bot":
        return "bot"
    return "human"


def _bitbucket_dc_actor_login(actor: object) -> str:
    if not isinstance(actor, dict):
        return ""
    return str(actor.get("name") or actor.get("slug") or "")


def _bitbucket_dc_actor_type(actor: object) -> str:
    if not isinstance(actor, dict):
        return "unknown"
    if actor.get("type") == "SERVICE":
        return "bot"
    return "human"


def _ado_actor_login(actor: object) -> str:
    if not isinstance(actor, dict):
        return ""
    return str(actor.get("uniqueName") or actor.get("displayName") or "")


def _ado_actor_type(actor: object) -> str:
    if not isinstance(actor, dict):
        return "unknown"
    unique_name = str(actor.get("uniqueName") or "").lower()
    if "service" in unique_name or actor.get("descriptor", "").startswith("svc:"):
        return "bot"
    return "human"
