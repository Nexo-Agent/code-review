from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

_ADO_COLUMNS = """
    ado_organization, ado_project, ado_pat,
    ado_webhook_username, ado_webhook_password
"""

_SELECT_COLUMNS = f"""
    id, project_id, name, git_provider, repo_full_name, llm_provider_id,
    github_webhook_secret, github_token, system_prompt, enabled,
    {_ADO_COLUMNS},
    created_at, updated_at
"""


@dataclass(frozen=True, slots=True)
class RepoIntegrationRow:
    id: UUID
    project_id: UUID
    name: str
    git_provider: str
    repo_full_name: str
    llm_provider_id: UUID | None
    github_webhook_secret: str
    github_token: str
    system_prompt: str
    enabled: bool
    ado_organization: str
    ado_project: str
    ado_pat: str
    ado_webhook_username: str
    ado_webhook_password: str
    created_at: datetime
    updated_at: datetime

    def matches_repo(self, repo_full_name: str) -> bool:
        configured = self.repo_full_name.strip()
        if not configured:
            return True
        return configured == repo_full_name.strip()


class RepoIntegrationRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_all(self) -> list[RepoIntegrationRow]:
        rows = await self._conn.fetch(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM repo_integrations
            ORDER BY repo_full_name ASC NULLS FIRST, name ASC
            """
        )
        return [_row_to_repo_integration(row) for row in rows]

    async def list_for_project(self, project_id: UUID) -> list[RepoIntegrationRow]:
        rows = await self._conn.fetch(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM repo_integrations
            WHERE project_id = $1
            ORDER BY repo_full_name ASC NULLS FIRST, name ASC
            """,
            project_id,
        )
        return [_row_to_repo_integration(row) for row in rows]

    async def list_for_team(
        self, team_id: UUID
    ) -> list[tuple[RepoIntegrationRow, str]]:
        rows = await self._conn.fetch(
            """
            SELECT ri.id, ri.project_id, ri.name, ri.git_provider, ri.repo_full_name,
                   ri.llm_provider_id, ri.github_webhook_secret, ri.github_token,
                   ri.system_prompt, ri.enabled, ri.ado_organization, ri.ado_project,
                   ri.ado_pat, ri.ado_webhook_username, ri.ado_webhook_password,
                   ri.created_at, ri.updated_at, p.name AS project_name
            FROM repo_integrations ri
            JOIN projects p ON p.id = ri.project_id
            WHERE p.team_id = $1
            ORDER BY p.name ASC, ri.repo_full_name ASC NULLS FIRST, ri.name ASC
            """,
            team_id,
        )
        return [(_row_to_repo_integration(row), row["project_name"]) for row in rows]

    async def list_for_teams(
        self, team_ids: list[UUID]
    ) -> list[tuple[RepoIntegrationRow, str, UUID, str]]:
        if not team_ids:
            return []
        rows = await self._conn.fetch(
            """
            SELECT ri.id, ri.project_id, ri.name, ri.git_provider, ri.repo_full_name,
                   ri.llm_provider_id, ri.github_webhook_secret, ri.github_token,
                   ri.system_prompt, ri.enabled, ri.ado_organization, ri.ado_project,
                   ri.ado_pat, ri.ado_webhook_username, ri.ado_webhook_password,
                   ri.created_at, ri.updated_at, p.name AS project_name,
                   p.team_id, t.name AS team_name
            FROM repo_integrations ri
            JOIN projects p ON p.id = ri.project_id
            JOIN teams t ON t.id = p.team_id
            WHERE p.team_id = ANY($1::uuid[])
            ORDER BY t.name ASC, p.name ASC,
                     ri.repo_full_name ASC NULLS FIRST, ri.name ASC
            """,
            team_ids,
        )
        return [
            (
                _row_to_repo_integration(row),
                row["project_name"],
                row["team_id"],
                row["team_name"],
            )
            for row in rows
        ]

    async def get(self, integration_id: UUID) -> RepoIntegrationRow | None:
        row = await self._conn.fetchrow(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM repo_integrations WHERE id = $1
            """,
            integration_id,
        )
        return _row_to_repo_integration(row) if row else None

    async def get_with_team(
        self, integration_id: UUID
    ) -> tuple[RepoIntegrationRow, UUID, UUID] | None:
        row = await self._conn.fetchrow(
            """
            SELECT ri.id, ri.project_id, ri.name, ri.git_provider, ri.repo_full_name,
                   ri.llm_provider_id, ri.github_webhook_secret, ri.github_token,
                   ri.system_prompt, ri.enabled, ri.ado_organization, ri.ado_project,
                   ri.ado_pat, ri.ado_webhook_username, ri.ado_webhook_password,
                   ri.created_at, ri.updated_at, p.team_id
            FROM repo_integrations ri
            JOIN projects p ON p.id = ri.project_id
            WHERE ri.id = $1
            """,
            integration_id,
        )
        if row is None:
            return None
        integration = _row_to_repo_integration(row)
        return integration, row["team_id"], integration.project_id

    async def resolve_for_repo(
        self,
        repo_full_name: str,
        *,
        project_id: UUID | None = None,
    ) -> RepoIntegrationRow | None:
        if project_id is not None:
            exact = await self._conn.fetchrow(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM repo_integrations
                WHERE enabled = true
                  AND project_id = $1
                  AND repo_full_name = $2
                LIMIT 1
                """,
                project_id,
                repo_full_name.strip(),
            )
            if exact:
                return _row_to_repo_integration(exact)
            catch_all = await self._conn.fetchrow(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM repo_integrations
                WHERE enabled = true AND project_id = $1 AND repo_full_name = ''
                LIMIT 1
                """,
                project_id,
            )
            return _row_to_repo_integration(catch_all) if catch_all else None

        exact = await self._conn.fetchrow(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM repo_integrations
            WHERE enabled = true AND repo_full_name = $1
            LIMIT 1
            """,
            repo_full_name.strip(),
        )
        if exact:
            return _row_to_repo_integration(exact)

        catch_all = await self._conn.fetchrow(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM repo_integrations
            WHERE enabled = true AND repo_full_name = ''
            LIMIT 1
            """
        )
        return _row_to_repo_integration(catch_all) if catch_all else None

    async def create(
        self,
        *,
        project_id: UUID,
        name: str,
        git_provider: str,
        repo_full_name: str,
        github_webhook_secret: str,
        github_token: str,
        system_prompt: str = "",
        enabled: bool = True,
        ado_organization: str = "",
        ado_project: str = "",
        ado_pat: str = "",
        ado_webhook_username: str = "",
        ado_webhook_password: str = "",
        llm_provider_id: UUID | None = None,
    ) -> RepoIntegrationRow:
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO repo_integrations (
                project_id, name, git_provider, repo_full_name, llm_provider_id,
                github_webhook_secret, github_token, system_prompt, enabled,
                ado_organization, ado_project, ado_pat,
                ado_webhook_username, ado_webhook_password
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING {_SELECT_COLUMNS}
            """,
            project_id,
            name,
            git_provider,
            repo_full_name.strip(),
            llm_provider_id,
            github_webhook_secret,
            github_token,
            system_prompt,
            enabled,
            ado_organization,
            ado_project,
            ado_pat,
            ado_webhook_username,
            ado_webhook_password,
        )
        if row is None:
            msg = "failed to create repo integration"
            raise RuntimeError(msg)
        return _row_to_repo_integration(row)

    async def update(
        self,
        integration_id: UUID,
        *,
        name: str | None = None,
        git_provider: str | None = None,
        repo_full_name: str | None = None,
        github_webhook_secret: str | None = None,
        github_token: str | None = None,
        system_prompt: str | None = None,
        enabled: bool | None = None,
        clear_webhook_secret: bool = False,
        clear_github_token: bool = False,
        ado_organization: str | None = None,
        ado_project: str | None = None,
        ado_pat: str | None = None,
        ado_webhook_username: str | None = None,
        ado_webhook_password: str | None = None,
        clear_ado_pat: bool = False,
        clear_ado_webhook_password: bool = False,
        llm_provider_id: UUID | None = None,
        clear_llm_provider_id: bool = False,
    ) -> RepoIntegrationRow:
        current = await self.get(integration_id)
        if current is None:
            msg = f"repo integration not found: {integration_id}"
            raise ValueError(msg)

        resolved_llm = current.llm_provider_id
        if clear_llm_provider_id:
            resolved_llm = None
        elif llm_provider_id is not None:
            resolved_llm = llm_provider_id

        row = await self._conn.fetchrow(
            f"""
            UPDATE repo_integrations
            SET name = $2,
                git_provider = $3,
                repo_full_name = $4,
                llm_provider_id = $18,
                github_webhook_secret = CASE
                    WHEN $12 THEN '' ELSE COALESCE($5, github_webhook_secret)
                END,
                github_token = CASE
                    WHEN $13 THEN '' ELSE COALESCE($6, github_token)
                END,
                system_prompt = COALESCE($7, system_prompt),
                enabled = $8,
                ado_organization = COALESCE($9, ado_organization),
                ado_project = COALESCE($10, ado_project),
                ado_pat = CASE
                    WHEN $14 THEN '' ELSE COALESCE($11, ado_pat)
                END,
                ado_webhook_username = COALESCE($15, ado_webhook_username),
                ado_webhook_password = CASE
                    WHEN $16 THEN '' ELSE COALESCE($17, ado_webhook_password)
                END,
                updated_at = now()
            WHERE id = $1
            RETURNING {_SELECT_COLUMNS}
            """,
            integration_id,
            name if name is not None else current.name,
            git_provider if git_provider is not None else current.git_provider,
            repo_full_name.strip()
            if repo_full_name is not None
            else current.repo_full_name,
            github_webhook_secret,
            github_token,
            system_prompt,
            enabled if enabled is not None else current.enabled,
            ado_organization,
            ado_project,
            ado_pat,
            ado_webhook_username,
            clear_webhook_secret,
            clear_github_token,
            clear_ado_pat,
            clear_ado_webhook_password,
            ado_webhook_password,
            resolved_llm,
        )
        if row is None:
            msg = "failed to update repo integration"
            raise RuntimeError(msg)
        return _row_to_repo_integration(row)

    async def delete(self, integration_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM repo_integrations WHERE id = $1",
            integration_id,
        )


def _row_to_repo_integration(row: asyncpg.Record) -> RepoIntegrationRow:
    return RepoIntegrationRow(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        git_provider=row["git_provider"],
        repo_full_name=row["repo_full_name"],
        llm_provider_id=row["llm_provider_id"],
        github_webhook_secret=row["github_webhook_secret"],
        github_token=row["github_token"],
        system_prompt=row["system_prompt"],
        enabled=row["enabled"],
        ado_organization=row["ado_organization"],
        ado_project=row["ado_project"],
        ado_pat=row["ado_pat"],
        ado_webhook_username=row["ado_webhook_username"],
        ado_webhook_password=row["ado_webhook_password"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
