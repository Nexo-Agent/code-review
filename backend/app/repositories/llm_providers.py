from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class LlmProviderRow:
    id: UUID
    organization_id: UUID
    name: str
    provider_id: str
    base_url: str
    api_token: str
    model: str
    opencode_model: str
    is_default: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @property
    def resolved_opencode_model(self) -> str:
        if self.opencode_model.strip():
            return self.opencode_model.strip()
        return f"{self.provider_id}/{self.model}"


_LLM_SELECT = """
    id, organization_id, name, provider_id, base_url, api_token,
    model, opencode_model, is_default, enabled, created_at, updated_at
"""


class LlmProviderRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_all(
        self, *, organization_id: UUID | None = None
    ) -> list[LlmProviderRow]:
        if organization_id is not None:
            rows = await self._conn.fetch(
                f"""
                SELECT {_LLM_SELECT}
                FROM llm_providers
                WHERE organization_id = $1
                ORDER BY is_default DESC, name ASC
                """,
                organization_id,
            )
        else:
            rows = await self._conn.fetch(
                f"""
                SELECT {_LLM_SELECT}
                FROM llm_providers
                ORDER BY is_default DESC, name ASC
                """
            )
        return [_row_to_llm_provider(row) for row in rows]

    async def list_paginated(
        self,
        *,
        organization_id: UUID,
        search: str = "",
        limit: int,
        offset: int,
    ) -> list[LlmProviderRow]:
        if search:
            pattern = f"%{search}%"
            rows = await self._conn.fetch(
                f"""
                SELECT {_LLM_SELECT}
                FROM llm_providers
                WHERE organization_id = $1 AND name ILIKE $2
                ORDER BY is_default DESC, name ASC
                LIMIT $3 OFFSET $4
                """,
                organization_id,
                pattern,
                limit,
                offset,
            )
        else:
            rows = await self._conn.fetch(
                f"""
                SELECT {_LLM_SELECT}
                FROM llm_providers
                WHERE organization_id = $1
                ORDER BY is_default DESC, name ASC
                LIMIT $2 OFFSET $3
                """,
                organization_id,
                limit,
                offset,
            )
        return [_row_to_llm_provider(row) for row in rows]

    async def count(
        self,
        *,
        organization_id: UUID,
        search: str = "",
    ) -> int:
        if search:
            pattern = f"%{search}%"
            return (
                await self._conn.fetchval(
                    """
                    SELECT COUNT(*)::int FROM llm_providers
                    WHERE organization_id = $1 AND name ILIKE $2
                    """,
                    organization_id,
                    pattern,
                )
                or 0
            )
        return (
            await self._conn.fetchval(
                "SELECT COUNT(*)::int FROM llm_providers WHERE organization_id = $1",
                organization_id,
            )
            or 0
        )

    async def get(self, provider_id: UUID) -> LlmProviderRow | None:
        row = await self._conn.fetchrow(
            f"""
            SELECT {_LLM_SELECT}
            FROM llm_providers WHERE id = $1
            """,
            provider_id,
        )
        return _row_to_llm_provider(row) if row else None

    async def get_default(
        self, *, organization_id: UUID | None = None
    ) -> LlmProviderRow | None:
        if organization_id is not None:
            row = await self._conn.fetchrow(
                f"""
                SELECT {_LLM_SELECT}
                FROM llm_providers
                WHERE is_default = true AND enabled = true AND organization_id = $1
                LIMIT 1
                """,
                organization_id,
            )
        else:
            row = await self._conn.fetchrow(
                f"""
                SELECT {_LLM_SELECT}
                FROM llm_providers
                WHERE is_default = true AND enabled = true
                LIMIT 1
                """
            )
        return _row_to_llm_provider(row) if row else None

    async def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        provider_id: str,
        base_url: str,
        api_token: str,
        model: str,
        opencode_model: str = "",
        is_default: bool = False,
        enabled: bool = True,
    ) -> LlmProviderRow:
        if is_default:
            await self._conn.execute(
                """
                UPDATE llm_providers SET is_default = false
                WHERE is_default = true AND organization_id = $1
                """,
                organization_id,
            )
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO llm_providers (
                organization_id, name, provider_id, base_url, api_token, model,
                opencode_model, is_default, enabled
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING {_LLM_SELECT}
            """,
            organization_id,
            name,
            provider_id,
            base_url,
            api_token,
            model,
            opencode_model,
            is_default,
            enabled,
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
        enabled: bool | None = None,
        clear_api_token: bool = False,
    ) -> LlmProviderRow:
        current = await self.get(provider_id)
        if current is None:
            msg = f"llm provider not found: {provider_id}"
            raise ValueError(msg)

        if is_default:
            await self._conn.execute(
                """
                UPDATE llm_providers SET is_default = false
                WHERE is_default = true AND organization_id = $1
                """,
                current.organization_id,
            )

        row = await self._conn.fetchrow(
            f"""
            UPDATE llm_providers
            SET name = $2,
                provider_id = $3,
                base_url = $4,
                api_token = CASE WHEN $9 THEN '' ELSE COALESCE($5, api_token) END,
                model = $6,
                opencode_model = $7,
                is_default = $8,
                enabled = $10,
                updated_at = now()
            WHERE id = $1
            RETURNING {_LLM_SELECT}
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
            enabled if enabled is not None else current.enabled,
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
        organization_id=row["organization_id"],
        name=row["name"],
        provider_id=row["provider_id"],
        base_url=row["base_url"],
        api_token=row["api_token"],
        model=row["model"],
        opencode_model=row["opencode_model"],
        is_default=row["is_default"],
        enabled=row["enabled"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
