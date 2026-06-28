from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class TeamMemberRow:
    team_id: UUID
    user_id: UUID
    role: str
    created_at: datetime
    user_email: str = ""
    user_name: str = ""
    team_name: str = ""


class TeamMemberRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_for_team(self, team_id: UUID) -> list[TeamMemberRow]:
        rows = await self._conn.fetch(
            """
            SELECT tm.team_id, tm.user_id, r.key AS role, tm.created_at,
                   u.email AS user_email, u.name AS user_name
            FROM team_members tm
            JOIN rbac_roles r ON r.id = tm.role_id
            JOIN users u ON u.id = tm.user_id
            WHERE tm.team_id = $1
            ORDER BY u.email ASC
            """,
            team_id,
        )
        return [_row_to_member(row) for row in rows]

    async def list_for_team_paginated(
        self,
        team_id: UUID,
        *,
        search: str = "",
        limit: int,
        offset: int,
    ) -> list[TeamMemberRow]:
        if search:
            pattern = f"%{search}%"
            rows = await self._conn.fetch(
                """
                SELECT tm.team_id, tm.user_id, r.key AS role, tm.created_at,
                       u.email AS user_email, u.name AS user_name
                FROM team_members tm
                JOIN rbac_roles r ON r.id = tm.role_id
                JOIN users u ON u.id = tm.user_id
                WHERE tm.team_id = $1
                  AND (u.email ILIKE $2 OR u.name ILIKE $2)
                ORDER BY u.email ASC
                LIMIT $3 OFFSET $4
                """,
                team_id,
                pattern,
                limit,
                offset,
            )
        else:
            rows = await self._conn.fetch(
                """
                SELECT tm.team_id, tm.user_id, r.key AS role, tm.created_at,
                       u.email AS user_email, u.name AS user_name
                FROM team_members tm
                JOIN rbac_roles r ON r.id = tm.role_id
                JOIN users u ON u.id = tm.user_id
                WHERE tm.team_id = $1
                ORDER BY u.email ASC
                LIMIT $2 OFFSET $3
                """,
                team_id,
                limit,
                offset,
            )
        return [_row_to_member(row) for row in rows]

    async def count_for_team(self, team_id: UUID, *, search: str = "") -> int:
        if search:
            pattern = f"%{search}%"
            return (
                await self._conn.fetchval(
                    """
                    SELECT COUNT(*)::int
                    FROM team_members tm
                    JOIN users u ON u.id = tm.user_id
                    WHERE tm.team_id = $1
                      AND (u.email ILIKE $2 OR u.name ILIKE $2)
                    """,
                    team_id,
                    pattern,
                )
                or 0
            )
        return (
            await self._conn.fetchval(
                "SELECT COUNT(*)::int FROM team_members WHERE team_id = $1",
                team_id,
            )
            or 0
        )

    async def get(self, team_id: UUID, user_id: UUID) -> TeamMemberRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT tm.team_id, tm.user_id, r.key AS role, tm.created_at,
                   u.email AS user_email, u.name AS user_name
            FROM team_members tm
            JOIN rbac_roles r ON r.id = tm.role_id
            JOIN users u ON u.id = tm.user_id
            WHERE tm.team_id = $1 AND tm.user_id = $2
            """,
            team_id,
            user_id,
        )
        return _row_to_member(row) if row else None

    async def list_team_ids_for_user(self, user_id: UUID) -> list[UUID]:
        rows = await self._conn.fetch(
            "SELECT team_id FROM team_members WHERE user_id = $1",
            user_id,
        )
        return [row["team_id"] for row in rows]

    async def is_member(self, team_id: UUID, user_id: UUID) -> bool:
        val = await self._conn.fetchval(
            """
            SELECT 1 FROM team_members
            WHERE team_id = $1 AND user_id = $2
            """,
            team_id,
            user_id,
        )
        return val is not None

    async def add(
        self,
        *,
        team_id: UUID,
        user_id: UUID,
        role: str = "member",
    ) -> TeamMemberRow:
        role_id = await self._conn.fetchval(
            "SELECT id FROM rbac_roles WHERE key = $1",
            role,
        )
        if role_id is None:
            msg = f"unknown team role: {role}"
            raise ValueError(msg)
        row = await self._conn.fetchrow(
            """
            INSERT INTO team_members (team_id, user_id, role_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (team_id, user_id) DO UPDATE SET role_id = EXCLUDED.role_id
            RETURNING team_id, user_id, created_at
            """,
            team_id,
            user_id,
            role_id,
        )
        if row is None:
            msg = "failed to add team member"
            raise RuntimeError(msg)
        member = await self.get(team_id, user_id)
        if member is None:
            msg = "failed to load team member after insert"
            raise RuntimeError(msg)
        return member

    async def remove(self, team_id: UUID, user_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM team_members WHERE team_id = $1 AND user_id = $2",
            team_id,
            user_id,
        )

    async def count_members_for_teams(self, team_ids: list[UUID]) -> dict[UUID, int]:
        if not team_ids:
            return {}
        rows = await self._conn.fetch(
            """
            SELECT team_id, COUNT(*)::int AS member_count
            FROM team_members
            WHERE team_id = ANY($1::uuid[])
            GROUP BY team_id
            """,
            team_ids,
        )
        return {row["team_id"]: row["member_count"] for row in rows}

    async def list_for_teams(self, team_ids: list[UUID]) -> list[TeamMemberRow]:
        if not team_ids:
            return []
        rows = await self._conn.fetch(
            """
            SELECT tm.team_id, tm.user_id, r.key AS role, tm.created_at,
                   u.email AS user_email, u.name AS user_name,
                   t.name AS team_name
            FROM team_members tm
            JOIN rbac_roles r ON r.id = tm.role_id
            JOIN users u ON u.id = tm.user_id
            JOIN teams t ON t.id = tm.team_id
            WHERE tm.team_id = ANY($1::uuid[])
            ORDER BY t.name ASC, u.email ASC
            """,
            team_ids,
        )
        return [_row_to_member(row) for row in rows]


def _row_to_member(row: asyncpg.Record) -> TeamMemberRow:
    return TeamMemberRow(
        team_id=row["team_id"],
        user_id=row["user_id"],
        role=row["role"],
        created_at=row["created_at"],
        user_email=row.get("user_email", ""),
        user_name=row.get("user_name", ""),
        team_name=row.get("team_name", ""),
    )
