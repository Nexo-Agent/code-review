from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class RepoIntegrationRow:
    id: UUID
    name: str
    git_provider: str
    repo_full_name: str
    github_webhook_secret: str
    github_token: str
    llm_provider_id: UUID | None
    system_prompt: str
    enabled: bool
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
            """
            SELECT id, name, git_provider, repo_full_name, github_webhook_secret,
                   github_token, llm_provider_id, system_prompt, enabled,
                   created_at, updated_at
            FROM repo_integrations
            ORDER BY repo_full_name ASC NULLS FIRST, name ASC
            """
        )
        return [_row_to_repo_integration(row) for row in rows]

    async def get(self, integration_id: UUID) -> RepoIntegrationRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, name, git_provider, repo_full_name, github_webhook_secret,
                   github_token, llm_provider_id, system_prompt, enabled,
                   created_at, updated_at
            FROM repo_integrations WHERE id = $1
            """,
            integration_id,
        )
        return _row_to_repo_integration(row) if row else None

    async def resolve_for_repo(self, repo_full_name: str) -> RepoIntegrationRow | None:
        exact = await self._conn.fetchrow(
            """
            SELECT id, name, git_provider, repo_full_name, github_webhook_secret,
                   github_token, llm_provider_id, system_prompt, enabled,
                   created_at, updated_at
            FROM repo_integrations
            WHERE enabled = true AND repo_full_name = $1
            LIMIT 1
            """,
            repo_full_name.strip(),
        )
        if exact:
            return _row_to_repo_integration(exact)

        catch_all = await self._conn.fetchrow(
            """
            SELECT id, name, git_provider, repo_full_name, github_webhook_secret,
                   github_token, llm_provider_id, system_prompt, enabled,
                   created_at, updated_at
            FROM repo_integrations
            WHERE enabled = true AND repo_full_name = ''
            LIMIT 1
            """
        )
        return _row_to_repo_integration(catch_all) if catch_all else None

    async def create(
        self,
        *,
        name: str,
        git_provider: str,
        repo_full_name: str,
        github_webhook_secret: str,
        github_token: str,
        llm_provider_id: UUID | None,
        system_prompt: str = "",
        enabled: bool = True,
    ) -> RepoIntegrationRow:
        row = await self._conn.fetchrow(
            """
            INSERT INTO repo_integrations (
                name, git_provider, repo_full_name, github_webhook_secret,
                github_token, llm_provider_id, system_prompt, enabled
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, name, git_provider, repo_full_name, github_webhook_secret,
                      github_token, llm_provider_id, system_prompt, enabled,
                      created_at, updated_at
            """,
            name,
            git_provider,
            repo_full_name.strip(),
            github_webhook_secret,
            github_token,
            llm_provider_id,
            system_prompt,
            enabled,
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
        llm_provider_id: UUID | None = None,
        clear_llm_provider_id: bool = False,
        system_prompt: str | None = None,
        enabled: bool | None = None,
        clear_webhook_secret: bool = False,
        clear_github_token: bool = False,
    ) -> RepoIntegrationRow:
        current = await self.get(integration_id)
        if current is None:
            msg = f"repo integration not found: {integration_id}"
            raise ValueError(msg)

        resolved_llm_id = current.llm_provider_id
        if clear_llm_provider_id:
            resolved_llm_id = None
        elif llm_provider_id is not None:
            resolved_llm_id = llm_provider_id

        row = await self._conn.fetchrow(
            """
            UPDATE repo_integrations
            SET name = $2,
                git_provider = $3,
                repo_full_name = $4,
                github_webhook_secret = CASE
                    WHEN $10 THEN '' ELSE COALESCE($5, github_webhook_secret)
                END,
                github_token = CASE
                    WHEN $11 THEN '' ELSE COALESCE($6, github_token)
                END,
                llm_provider_id = $7,
                system_prompt = COALESCE($8, system_prompt),
                enabled = $9,
                updated_at = now()
            WHERE id = $1
            RETURNING id, name, git_provider, repo_full_name, github_webhook_secret,
                      github_token, llm_provider_id, system_prompt, enabled,
                      created_at, updated_at
            """,
            integration_id,
            name if name is not None else current.name,
            git_provider if git_provider is not None else current.git_provider,
            repo_full_name.strip()
            if repo_full_name is not None
            else current.repo_full_name,
            github_webhook_secret
            if github_webhook_secret is not None
            else current.github_webhook_secret,
            github_token if github_token is not None else current.github_token,
            resolved_llm_id,
            system_prompt,
            enabled if enabled is not None else current.enabled,
            clear_webhook_secret,
            clear_github_token,
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
        name=row["name"],
        git_provider=row["git_provider"],
        repo_full_name=row["repo_full_name"],
        github_webhook_secret=row["github_webhook_secret"],
        github_token=row["github_token"],
        llm_provider_id=row["llm_provider_id"],
        system_prompt=row["system_prompt"],
        enabled=row["enabled"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
