from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class ReviewRow:
    id: UUID
    provider: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    status: str
    delivery_id: str | None
    repo_integration_id: UUID | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ReviewRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, review_id: UUID) -> ReviewRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, provider, repo_full_name, pr_number, head_sha, status,
                   delivery_id, repo_integration_id, error_message, started_at,
                   completed_at, created_at
            FROM reviews WHERE id = $1
            """,
            review_id,
        )
        return _row_to_review(row) if row else None

    async def update_status(
        self,
        review_id: UUID,
        *,
        status: str,
        error_message: str | None = None,
        set_started: bool = False,
        set_completed: bool = False,
    ) -> ReviewRow | None:
        row = await self._conn.fetchrow(
            """
            UPDATE reviews
            SET status = $2,
                error_message = COALESCE($3, error_message),
                started_at = CASE
                    WHEN $4 THEN COALESCE(started_at, now())
                    ELSE started_at
                END,
                completed_at = CASE WHEN $5 THEN now() ELSE completed_at END
            WHERE id = $1
            RETURNING id, provider, repo_full_name, pr_number, head_sha, status,
                      delivery_id, repo_integration_id, error_message, started_at,
                      completed_at, created_at
            """,
            review_id,
            status,
            error_message,
            set_started,
            set_completed,
        )
        return _row_to_review(row) if row else None

    async def replace_findings(
        self,
        review_id: UUID,
        findings: list[dict[str, object]],
    ) -> None:
        async with self._conn.transaction():
            await self._conn.execute(
                "DELETE FROM review_findings WHERE review_id = $1",
                review_id,
            )
            for finding in findings:
                await self._conn.execute(
                    """
                    INSERT INTO review_findings (
                        review_id, severity, file_path,
                        line_start, line_end, title, body
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    review_id,
                    finding["severity"],
                    finding.get("file_path"),
                    finding.get("line_start"),
                    finding.get("line_end"),
                    finding["title"],
                    finding["body"],
                )


def _row_to_review(row: asyncpg.Record) -> ReviewRow:
    return ReviewRow(
        id=row["id"],
        provider=row["provider"],
        repo_full_name=row["repo_full_name"],
        pr_number=row["pr_number"],
        head_sha=row["head_sha"],
        status=row["status"],
        delivery_id=row["delivery_id"],
        repo_integration_id=row["repo_integration_id"],
        error_message=row["error_message"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
    )
