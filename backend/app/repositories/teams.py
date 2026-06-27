from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

DEFAULT_TEAM_ID = UUID("00000000-0000-4000-8000-000000000002")


@dataclass(frozen=True, slots=True)
class TeamRow:
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    created_at: datetime


class TeamRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_all(self, *, organization_id: UUID | None = None) -> list[TeamRow]:
        if organization_id is not None:
            rows = await self._conn.fetch(
                """
                SELECT id, organization_id, name, slug, created_at
                FROM teams
                WHERE organization_id = $1
                ORDER BY name ASC
                """,
                organization_id,
            )
        else:
            rows = await self._conn.fetch(
                """
                SELECT id, organization_id, name, slug, created_at
                FROM teams
                ORDER BY name ASC
                """
            )
        return [_row_to_team(row) for row in rows]

    async def list_for_user(self, user_id: UUID) -> list[TeamRow]:
        rows = await self._conn.fetch(
            """
            SELECT t.id, t.organization_id, t.name, t.slug, t.created_at
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.id
            WHERE tm.user_id = $1
            ORDER BY t.name ASC
            """,
            user_id,
        )
        return [_row_to_team(row) for row in rows]

    async def get(self, team_id: UUID) -> TeamRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, organization_id, name, slug, created_at
            FROM teams WHERE id = $1
            """,
            team_id,
        )
        return _row_to_team(row) if row else None

    async def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        slug: str,
    ) -> TeamRow:
        row = await self._conn.fetchrow(
            """
            INSERT INTO teams (organization_id, name, slug)
            VALUES ($1, $2, $3)
            RETURNING id, organization_id, name, slug, created_at
            """,
            organization_id,
            name,
            slug,
        )
        if row is None:
            msg = "failed to create team"
            raise RuntimeError(msg)
        return _row_to_team(row)

    async def update(
        self,
        team_id: UUID,
        *,
        name: str | None = None,
        slug: str | None = None,
    ) -> TeamRow | None:
        current = await self.get(team_id)
        if current is None:
            return None
        row = await self._conn.fetchrow(
            """
            UPDATE teams
            SET name = $2, slug = $3
            WHERE id = $1
            RETURNING id, organization_id, name, slug, created_at
            """,
            team_id,
            name if name is not None else current.name,
            slug if slug is not None else current.slug,
        )
        return _row_to_team(row) if row else None

    async def delete(self, team_id: UUID) -> None:
        await self._conn.execute("DELETE FROM teams WHERE id = $1", team_id)

    async def count_repos_for_teams(self, team_ids: list[UUID]) -> dict[UUID, int]:
        if not team_ids:
            return {}
        rows = await self._conn.fetch(
            """
            SELECT p.team_id, COUNT(ri.id)::int AS repo_count
            FROM repo_integrations ri
            JOIN projects p ON p.id = ri.project_id
            WHERE p.team_id = ANY($1::uuid[])
            GROUP BY p.team_id
            """,
            team_ids,
        )
        return {row["team_id"]: row["repo_count"] for row in rows}


def _row_to_team(row: asyncpg.Record) -> TeamRow:
    return TeamRow(
        id=row["id"],
        organization_id=row["organization_id"],
        name=row["name"],
        slug=row["slug"],
        created_at=row["created_at"],
    )
