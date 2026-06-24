from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class ExampleRow:
    id: UUID
    name: str
    created_at: datetime


class ExampleRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list(self) -> list[ExampleRow]:
        rows = await self._conn.fetch(
            "SELECT id, name, created_at FROM examples ORDER BY created_at DESC"
        )
        return [_row_to_example(row) for row in rows]

    async def create(self, name: str) -> ExampleRow:
        row = await self._conn.fetchrow(
            """
            INSERT INTO examples (name)
            VALUES ($1)
            RETURNING id, name, created_at
            """,
            name,
        )
        if row is None:
            msg = "Failed to create example"
            raise RuntimeError(msg)
        return _row_to_example(row)

    async def get(self, example_id: UUID) -> ExampleRow | None:
        row = await self._conn.fetchrow(
            "SELECT id, name, created_at FROM examples WHERE id = $1",
            example_id,
        )
        return _row_to_example(row) if row else None


def _row_to_example(row: asyncpg.Record) -> ExampleRow:
    return ExampleRow(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
    )
