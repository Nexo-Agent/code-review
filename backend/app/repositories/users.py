from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class UserRow:
    id: UUID
    oidc_sub: str
    email: str
    name: str
    is_org_admin: bool
    created_at: datetime


class UserRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, user_id: UUID) -> UserRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, oidc_sub, email, name, is_org_admin, created_at
            FROM users WHERE id = $1
            """,
            user_id,
        )
        return _row_to_user(row) if row else None

    async def get_by_oidc_sub(self, oidc_sub: str) -> UserRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, oidc_sub, email, name, is_org_admin, created_at
            FROM users WHERE oidc_sub = $1
            """,
            oidc_sub,
        )
        return _row_to_user(row) if row else None

    async def list_all(self) -> list[UserRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, oidc_sub, email, name, is_org_admin, created_at
            FROM users
            ORDER BY email ASC
            """
        )
        return [_row_to_user(row) for row in rows]

    async def count_org_admins(self) -> int:
        return await self._conn.fetchval(
            "SELECT COUNT(*)::int FROM users WHERE is_org_admin = true"
        )

    async def upsert_oidc_user(
        self,
        *,
        oidc_sub: str,
        email: str,
        name: str,
        is_org_admin: bool = False,
    ) -> UserRow:
        row = await self._conn.fetchrow(
            """
            INSERT INTO users (oidc_sub, email, name, is_org_admin)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (oidc_sub) DO UPDATE
            SET email = EXCLUDED.email,
                name = CASE
                    WHEN EXCLUDED.name <> '' THEN EXCLUDED.name
                    ELSE users.name
                END
            RETURNING id, oidc_sub, email, name, is_org_admin, created_at
            """,
            oidc_sub,
            email,
            name,
            is_org_admin,
        )
        if row is None:
            msg = "failed to upsert user"
            raise RuntimeError(msg)
        return _row_to_user(row)

    async def set_org_admin(
        self, user_id: UUID, *, is_org_admin: bool
    ) -> UserRow | None:
        row = await self._conn.fetchrow(
            """
            UPDATE users SET is_org_admin = $2 WHERE id = $1
            RETURNING id, oidc_sub, email, name, is_org_admin, created_at
            """,
            user_id,
            is_org_admin,
        )
        return _row_to_user(row) if row else None


def _row_to_user(row: asyncpg.Record) -> UserRow:
    return UserRow(
        id=row["id"],
        oidc_sub=row["oidc_sub"],
        email=row["email"],
        name=row["name"],
        is_org_admin=row["is_org_admin"],
        created_at=row["created_at"],
    )
