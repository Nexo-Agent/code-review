from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

DEFAULT_ORG_ID = UUID("00000000-0000-4000-8000-000000000001")


@dataclass(frozen=True, slots=True)
class OrganizationRow:
    id: UUID
    name: str
    created_at: datetime


class OrganizationRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_default(self) -> OrganizationRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, name, created_at
            FROM organizations
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        return _row_to_organization(row) if row else None

    async def get(self, organization_id: UUID) -> OrganizationRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, name, created_at
            FROM organizations WHERE id = $1
            """,
            organization_id,
        )
        return _row_to_organization(row) if row else None


def _row_to_organization(row: asyncpg.Record) -> OrganizationRow:
    return OrganizationRow(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
    )
