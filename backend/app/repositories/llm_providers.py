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

    async def list_all(self) -> list[LlmProviderRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, name, provider_id, base_url, api_token, model,
                   opencode_model, is_default, created_at, updated_at
            FROM llm_providers
            ORDER BY is_default DESC, name ASC
            """
        )
        return [_row_to_llm_provider(row) for row in rows]

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

    async def create(
        self,
        *,
        name: str,
        provider_id: str,
        base_url: str,
        api_token: str,
        model: str,
        opencode_model: str = "",
        is_default: bool = False,
    ) -> LlmProviderRow:
        if is_default:
            await self._conn.execute(
                "UPDATE llm_providers SET is_default = false WHERE is_default = true"
            )
        row = await self._conn.fetchrow(
            """
            INSERT INTO llm_providers (
                name, provider_id, base_url, api_token, model,
                opencode_model, is_default
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, name, provider_id, base_url, api_token, model,
                      opencode_model, is_default, created_at, updated_at
            """,
            name,
            provider_id,
            base_url,
            api_token,
            model,
            opencode_model,
            is_default,
        )
        if row is None:
            msg = "failed to create llm provider"
            raise RuntimeError(msg)
        return _row_to_llm_provider(row)

    async def update(
        self,
        provider_id: UUID,
        *,
        name: str | None = None,
        provider_id_key: str | None = None,
        base_url: str | None = None,
        api_token: str | None = None,
        model: str | None = None,
        opencode_model: str | None = None,
        is_default: bool | None = None,
        clear_api_token: bool = False,
    ) -> LlmProviderRow:
        current = await self.get(provider_id)
        if current is None:
            msg = f"llm provider not found: {provider_id}"
            raise ValueError(msg)

        if is_default:
            await self._conn.execute(
                "UPDATE llm_providers SET is_default = false WHERE is_default = true"
            )

        row = await self._conn.fetchrow(
            """
            UPDATE llm_providers
            SET name = $2,
                provider_id = $3,
                base_url = $4,
                api_token = CASE WHEN $10 THEN '' ELSE COALESCE($5, api_token) END,
                model = $6,
                opencode_model = $7,
                is_default = $8,
                updated_at = now()
            WHERE id = $1
            RETURNING id, name, provider_id, base_url, api_token, model,
                      opencode_model, is_default, created_at, updated_at
            """,
            provider_id,
            name if name is not None else current.name,
            provider_id_key if provider_id_key is not None else current.provider_id,
            base_url if base_url is not None else current.base_url,
            api_token if api_token is not None else current.api_token,
            model if model is not None else current.model,
            opencode_model if opencode_model is not None else current.opencode_model,
            is_default if is_default is not None else current.is_default,
            clear_api_token,
        )
        if row is None:
            msg = "failed to update llm provider"
            raise RuntimeError(msg)
        return _row_to_llm_provider(row)

    async def delete(self, provider_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM llm_providers WHERE id = $1",
            provider_id,
        )


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
