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

_FEEDBACK_KEYWORDS: dict[str, tuple[str, str]] = {
    "helpful": ("quality_feedback", "helpful"),
    "not helpful": ("quality_feedback", "not_helpful"),
    "fixed": ("resolution_feedback", "fixed"),
    "applied": ("resolution_feedback", "applied"),
    "dismissed": ("resolution_feedback", "dismissed"),
    "deferred": ("resolution_feedback", "deferred"),
}
_TRAILING_PUNCTUATION_RE = re.compile(r"[.!?]+$")


def supports_review_analytics(git_provider: str) -> bool:
    return git_provider == "github"


def normalize_feedback_keyword(body: str) -> dict[str, str] | None:
    normalized = _TRAILING_PUNCTUATION_RE.sub("", body.strip().lower())
    classification = _FEEDBACK_KEYWORDS.get(normalized)
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
    if repo_integration.git_provider == "github":
        return await _ingest_github_analytics_event(
            conn,
            repo_integration=repo_integration,
            body=body,
            headers=headers,
        )
    return 0


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
    event_at = _parse_github_timestamp(str(comment.get("created_at") or ""))
    actor_login = _github_actor_login(sender)
    comment_id = str(comment.get("id") or "")
    body = str(comment.get("body") or "")
    inserted = 0
    raw_event = await repo.insert_engagement_event(
        provider="github",
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
        provider_delivery_id=delivery_id,
        provider_event_id="created",
        provider_object_id=comment_id,
        dedup_key=f"github:{delivery_id}:human_replied:{comment_id}",
        payload_json=payload,
        normalized_json={
            "parent_remote_comment_id": artifact.remote_comment_id,
            "body": body,
        },
    )
    if raw_event is not None:
        inserted += 1
    feedback = normalize_feedback_keyword(body)
    if feedback is None:
        return inserted
    classified = await repo.insert_engagement_event(
        provider="github",
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
        provider_delivery_id=delivery_id,
        provider_event_id="created",
        provider_object_id=comment_id,
        dedup_key=f"github:{delivery_id}:feedback_classified:{comment_id}",
        payload_json=payload,
        normalized_json=feedback,
    )
    if classified is not None:
        inserted += 1
    return inserted


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


def _github_pull_request_event_time(event_type: str, pull_request: dict) -> datetime:
    if event_type == "pr_opened":
        return _parse_github_timestamp(str(pull_request.get("created_at") or ""))
    if event_type == "pr_merged":
        merged_at = str(pull_request.get("merged_at") or "")
        if merged_at:
            return _parse_github_timestamp(merged_at)
    updated_at = str(pull_request.get("updated_at") or "")
    if updated_at:
        return _parse_github_timestamp(updated_at)
    return datetime.now(tz=UTC)


def _parse_github_timestamp(value: str) -> datetime:
    if not value.strip():
        return datetime.now(tz=UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


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
