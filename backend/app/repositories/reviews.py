from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

_REVIEW_SELECT = """
    id, provider, repo_full_name, pr_number, pr_title,
    pr_url, pr_author, head_sha, base_sha, base_ref, head_ref,
    status, delivery_id, repo_integration_id, error_message,
    started_at, completed_at, created_at,
    summary_comment_posted, inline_comments_posted, inline_comments_skipped
"""


@dataclass(frozen=True, slots=True)
class ReviewRow:
    id: UUID
    provider: str
    repo_full_name: str
    pr_number: int
    pr_title: str
    pr_url: str
    pr_author: str
    head_sha: str
    base_sha: str
    base_ref: str
    head_ref: str
    status: str
    delivery_id: str | None
    repo_integration_id: UUID | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    summary_comment_posted: bool = False
    inline_comments_posted: int = 0
    inline_comments_skipped: int = 0
    findings_count: int = 0


@dataclass(frozen=True, slots=True)
class ReviewFindingRow:
    id: UUID
    review_id: UUID
    severity: str
    file_path: str | None
    line_start: int | None
    line_end: int | None
    title: str
    body: str
    created_at: datetime


class ReviewRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_reviews(
        self,
        *,
        status: str | None = None,
        repo_full_name: str | None = None,
        pr_number: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReviewRow]:
        clauses = ["1=1"]
        args: list[object] = []
        idx = 1
        if status:
            clauses.append(f"status = ${idx}")
            args.append(status)
            idx += 1
        if repo_full_name:
            clauses.append(f"repo_full_name = ${idx}")
            args.append(repo_full_name)
            idx += 1
        if pr_number is not None:
            clauses.append(f"pr_number = ${idx}")
            args.append(pr_number)
            idx += 1
        args.extend([limit, offset])
        query = f"""
            SELECT r.id, r.provider, r.repo_full_name, r.pr_number, r.pr_title,
                   r.pr_url, r.pr_author, r.head_sha, r.base_sha, r.base_ref,
                   r.head_ref, r.status, r.delivery_id, r.repo_integration_id,
                   r.error_message, r.started_at, r.completed_at, r.created_at,
                   r.summary_comment_posted, r.inline_comments_posted,
                   r.inline_comments_skipped,
                   (
                       SELECT COUNT(*)::int
                       FROM review_findings rf
                       WHERE rf.review_id = r.id
                   ) AS findings_count
            FROM reviews r
            WHERE {" AND ".join(clauses)}
            ORDER BY r.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        rows = await self._conn.fetch(query, *args)
        return [_row_to_review(row) for row in rows]

    async def get(self, review_id: UUID) -> ReviewRow | None:
        row = await self._conn.fetchrow(
            f"SELECT {_REVIEW_SELECT} FROM reviews WHERE id = $1",
            review_id,
        )
        return _row_to_review(row) if row else None

    async def get_by_delivery_id(self, delivery_id: str) -> ReviewRow | None:
        row = await self._conn.fetchrow(
            f"SELECT {_REVIEW_SELECT} FROM reviews WHERE delivery_id = $1",
            delivery_id,
        )
        return _row_to_review(row) if row else None

    async def create(
        self,
        *,
        provider: str,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        delivery_id: str | None,
        repo_integration_id: UUID | None = None,
        pr_title: str = "",
        pr_url: str = "",
        pr_author: str = "",
        base_sha: str = "",
        base_ref: str = "",
        head_ref: str = "",
    ) -> ReviewRow:
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO reviews (
                provider, repo_full_name, pr_number, pr_title, pr_url, pr_author,
                head_sha, base_sha, base_ref, head_ref, status,
                delivery_id, repo_integration_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending', $11, $12)
            RETURNING {_REVIEW_SELECT}
            """,
            provider,
            repo_full_name,
            pr_number,
            pr_title,
            pr_url,
            pr_author,
            head_sha,
            base_sha,
            base_ref,
            head_ref,
            delivery_id,
            repo_integration_id,
        )
        if row is None:
            existing = (
                await self.get_by_delivery_id(delivery_id) if delivery_id else None
            )
            if existing:
                return existing
            msg = "Failed to create review"
            raise RuntimeError(msg)
        return _row_to_review(row)

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
            f"""
            UPDATE reviews
            SET status = $2,
                error_message = COALESCE($3, error_message),
                started_at = CASE
                    WHEN $4 THEN COALESCE(started_at, now())
                    ELSE started_at
                END,
                completed_at = CASE WHEN $5 THEN now() ELSE completed_at END
            WHERE id = $1
            RETURNING {_REVIEW_SELECT}
            """,
            review_id,
            status,
            error_message,
            set_started,
            set_completed,
        )
        return _row_to_review(row) if row else None

    async def update_request_metadata(
        self,
        review_id: UUID,
        *,
        pr_title: str = "",
        pr_url: str = "",
        pr_author: str = "",
        head_sha: str = "",
        base_sha: str = "",
        base_ref: str = "",
        head_ref: str = "",
    ) -> None:
        await self._conn.execute(
            """
            UPDATE reviews
            SET pr_title = CASE WHEN $2 <> '' THEN $2 ELSE pr_title END,
                pr_url = CASE WHEN $3 <> '' THEN $3 ELSE pr_url END,
                pr_author = CASE WHEN $4 <> '' THEN $4 ELSE pr_author END,
                head_sha = CASE WHEN $5 <> '' THEN $5 ELSE head_sha END,
                base_sha = CASE WHEN $6 <> '' THEN $6 ELSE base_sha END,
                base_ref = CASE WHEN $7 <> '' THEN $7 ELSE base_ref END,
                head_ref = CASE WHEN $8 <> '' THEN $8 ELSE head_ref END
            WHERE id = $1
            """,
            review_id,
            pr_title,
            pr_url,
            pr_author,
            head_sha,
            base_sha,
            base_ref,
            head_ref,
        )

    async def update_delivery_stats(
        self,
        review_id: UUID,
        *,
        summary_comment_posted: bool,
        inline_comments_posted: int,
        inline_comments_skipped: int,
    ) -> None:
        await self._conn.execute(
            """
            UPDATE reviews
            SET summary_comment_posted = $2,
                inline_comments_posted = $3,
                inline_comments_skipped = $4
            WHERE id = $1
            """,
            review_id,
            summary_comment_posted,
            inline_comments_posted,
            inline_comments_skipped,
        )

    async def reset_for_retry(self, review_id: UUID) -> ReviewRow | None:
        async with self._conn.transaction():
            await self._conn.execute(
                "DELETE FROM review_findings WHERE review_id = $1",
                review_id,
            )
            row = await self._conn.fetchrow(
                f"""
                UPDATE reviews
                SET status = 'pending',
                    error_message = NULL,
                    started_at = NULL,
                    completed_at = NULL,
                    summary_comment_posted = false,
                    inline_comments_posted = 0,
                    inline_comments_skipped = 0
                WHERE id = $1
                RETURNING {_REVIEW_SELECT}
                """,
                review_id,
            )
        return _row_to_review(row) if row else None

    async def list_findings(self, review_id: UUID) -> list[ReviewFindingRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, review_id, severity, file_path, line_start, line_end,
                   title, body, created_at
            FROM review_findings
            WHERE review_id = $1
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 0
                    WHEN 'warning' THEN 1
                    WHEN 'info' THEN 2
                    ELSE 3
                END,
                created_at
            """,
            review_id,
        )
        return [_row_to_finding(row) for row in rows]

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
        pr_title=row["pr_title"],
        pr_url=row["pr_url"],
        pr_author=row["pr_author"],
        head_sha=row["head_sha"],
        base_sha=row["base_sha"],
        base_ref=row["base_ref"],
        head_ref=row["head_ref"],
        status=row["status"],
        delivery_id=row["delivery_id"],
        repo_integration_id=row["repo_integration_id"],
        error_message=row["error_message"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
        summary_comment_posted=row["summary_comment_posted"],
        inline_comments_posted=row["inline_comments_posted"],
        inline_comments_skipped=row["inline_comments_skipped"],
        findings_count=row["findings_count"] if "findings_count" in row else 0,
    )


def _row_to_finding(row: asyncpg.Record) -> ReviewFindingRow:
    return ReviewFindingRow(
        id=row["id"],
        review_id=row["review_id"],
        severity=row["severity"],
        file_path=row["file_path"],
        line_start=row["line_start"],
        line_end=row["line_end"],
        title=row["title"],
        body=row["body"],
        created_at=row["created_at"],
    )
