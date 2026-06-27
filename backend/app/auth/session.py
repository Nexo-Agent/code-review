import json
import secrets
from uuid import UUID

import redis.asyncio as redis

from app.config import get_code_review_settings

SESSION_PREFIX = "cogito:session:"


def _redis_client() -> redis.Redis:
    settings = get_code_review_settings()
    return redis.from_url(settings.celery_broker_url, decode_responses=True)


async def create_session(*, user_id: UUID) -> str:
    session_id = secrets.token_urlsafe(32)
    payload = json.dumps({"user_id": str(user_id)})
    client = _redis_client()
    try:
        settings = get_code_review_settings()
        await client.setex(
            f"{SESSION_PREFIX}{session_id}",
            settings.session_ttl_seconds,
            payload,
        )
    finally:
        await client.aclose()
    return session_id


async def get_session_user_id(session_id: str) -> UUID | None:
    client = _redis_client()
    try:
        raw = await client.get(f"{SESSION_PREFIX}{session_id}")
    finally:
        await client.aclose()
    if not raw:
        return None
    data = json.loads(raw)
    return UUID(data["user_id"])


async def destroy_session(session_id: str) -> None:
    client = _redis_client()
    try:
        await client.delete(f"{SESSION_PREFIX}{session_id}")
    finally:
        await client.aclose()
