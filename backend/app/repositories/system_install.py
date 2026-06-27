from dataclasses import dataclass
from datetime import datetime

import asyncpg


@dataclass(frozen=True, slots=True)
class SystemInstallRow:
    completed_at: datetime | None


class SystemInstallRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self) -> SystemInstallRow | None:
        row = await self._conn.fetchrow(
            "SELECT completed_at FROM system_install WHERE singleton = true"
        )
        if row is None:
            return None
        return SystemInstallRow(completed_at=row["completed_at"])

    async def is_setup_required(self) -> bool:
        row = await self.get()
        if row is None:
            return True
        return row.completed_at is None

    async def mark_completed(self) -> None:
        await self._conn.execute(
            """
            UPDATE system_install
            SET completed_at = now()
            WHERE singleton = true AND completed_at IS NULL
            """
        )
