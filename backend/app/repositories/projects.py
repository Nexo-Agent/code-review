from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

DEFAULT_PROJECT_ID = UUID("00000000-0000-4000-8000-000000000003")


@dataclass(frozen=True, slots=True)
class ProjectRow:
    id: UUID
    team_id: UUID
    name: str
    description: str
    llm_provider_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ProjectRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_for_team(self, team_id: UUID) -> list[ProjectRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, team_id, name, description, llm_provider_id,
                   created_at, updated_at
            FROM projects
            WHERE team_id = $1
            ORDER BY name ASC
            """,
            team_id,
        )
        return [_row_to_project(row) for row in rows]

    async def get(self, project_id: UUID) -> ProjectRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, team_id, name, description, llm_provider_id,
                   created_at, updated_at
            FROM projects WHERE id = $1
            """,
            project_id,
        )
        return _row_to_project(row) if row else None

    async def get_with_team(self, project_id: UUID) -> tuple[ProjectRow, UUID] | None:
        row = await self._conn.fetchrow(
            """
            SELECT p.id, p.team_id, p.name, p.description, p.llm_provider_id,
                   p.created_at, p.updated_at, t.organization_id
            FROM projects p
            JOIN teams t ON t.id = p.team_id
            WHERE p.id = $1
            """,
            project_id,
        )
        if row is None:
            return None
        project = _row_to_project(row)
        return project, row["organization_id"]

    async def create(
        self,
        *,
        team_id: UUID,
        name: str,
        description: str = "",
        llm_provider_id: UUID | None = None,
    ) -> ProjectRow:
        row = await self._conn.fetchrow(
            """
            INSERT INTO projects (team_id, name, description, llm_provider_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id, team_id, name, description, llm_provider_id,
                      created_at, updated_at
            """,
            team_id,
            name,
            description,
            llm_provider_id,
        )
        if row is None:
            msg = "failed to create project"
            raise RuntimeError(msg)
        return _row_to_project(row)

    async def update(
        self,
        project_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        llm_provider_id: UUID | None = None,
        clear_llm_provider_id: bool = False,
    ) -> ProjectRow | None:
        current = await self.get(project_id)
        if current is None:
            return None

        resolved_llm = current.llm_provider_id
        if clear_llm_provider_id:
            resolved_llm = None
        elif llm_provider_id is not None:
            resolved_llm = llm_provider_id

        row = await self._conn.fetchrow(
            """
            UPDATE projects
            SET name = $2,
                description = $3,
                llm_provider_id = $4,
                updated_at = now()
            WHERE id = $1
            RETURNING id, team_id, name, description, llm_provider_id,
                      created_at, updated_at
            """,
            project_id,
            name if name is not None else current.name,
            description if description is not None else current.description,
            resolved_llm,
        )
        return _row_to_project(row) if row else None

    async def delete(self, project_id: UUID) -> None:
        await self._conn.execute("DELETE FROM projects WHERE id = $1", project_id)


def _row_to_project(row: asyncpg.Record) -> ProjectRow:
    return ProjectRow(
        id=row["id"],
        team_id=row["team_id"],
        name=row["name"],
        description=row["description"],
        llm_provider_id=row["llm_provider_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
