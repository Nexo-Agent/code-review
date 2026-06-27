import json
import secrets

import redis.asyncio as redis

from app.config import get_code_review_settings

AUTH_STATE_PREFIX = "cogito:auth-state:"
AUTH_STATE_TTL_SECONDS = 600


def _redis_client() -> redis.Redis:
    settings = get_code_review_settings()
    return redis.from_url(settings.celery_broker_url, decode_responses=True)


async def create_auth_state(*, return_to: str) -> str:
    state = secrets.token_urlsafe(32)
    payload = json.dumps({"return_to": return_to})
    client = _redis_client()
    try:
        await client.setex(
            f"{AUTH_STATE_PREFIX}{state}",
            AUTH_STATE_TTL_SECONDS,
            payload,
        )
    finally:
        await client.aclose()
    return state


async def consume_auth_state(state: str) -> str | None:
    if not state:
        return None
    client = _redis_client()
    key = f"{AUTH_STATE_PREFIX}{state}"
    try:
        raw = await client.get(key)
        if raw:
            await client.delete(key)
    finally:
        await client.aclose()
    if not raw:
        return None
    data = json.loads(raw)
    return data.get("return_to")
