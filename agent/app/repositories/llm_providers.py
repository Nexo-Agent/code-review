from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class LlmProviderRow:
    id: UUID
    name: str
    provider_id: str
    base_url: str
    api_token: str
    model: str
    opencode_model: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    @property
    def resolved_opencode_model(self) -> str:
        if self.opencode_model.strip():
            return self.opencode_model.strip()
        return f"{self.provider_id}/{self.model}"


class LlmProviderRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, provider_id: UUID) -> LlmProviderRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, name, provider_id, base_url, api_token, model,
                   opencode_model, is_default, created_at, updated_at
            FROM llm_providers WHERE id = $1
            """,
            provider_id,
        )
        return _row_to_llm_provider(row) if row else None

    async def get_default(self) -> LlmProviderRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, name, provider_id, base_url, api_token, model,
                   opencode_model, is_default, created_at, updated_at
            FROM llm_providers
            WHERE is_default = true
            LIMIT 1
            """
        )
        if row:
            return _row_to_llm_provider(row)
        row = await self._conn.fetchrow(
            """
            SELECT id, name, provider_id, base_url, api_token, model,
                   opencode_model, is_default, created_at, updated_at
            FROM llm_providers
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        return _row_to_llm_provider(row) if row else None


def _row_to_llm_provider(row: asyncpg.Record) -> LlmProviderRow:
    return LlmProviderRow(
        id=row["id"],
        name=row["name"],
        provider_id=row["provider_id"],
        base_url=row["base_url"],
        api_token=row["api_token"],
        model=row["model"],
        opencode_model=row["opencode_model"],
        is_default=row["is_default"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
