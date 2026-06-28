import json
from uuid import UUID

import asyncpg


async def log_audit_event(
    conn: asyncpg.Connection,
    *,
    actor_user_id: UUID | None,
    event_type: str,
    target_type: str = "",
    target_id: str = "",
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO audit_events (
            actor_user_id, event_type, target_type, target_id,
            before_state, after_state
        )
        VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
        """,
        actor_user_id,
        event_type,
        target_type,
        target_id,
        json.dumps(before_state) if before_state is not None else None,
        json.dumps(after_state) if after_state is not None else None,
    )
