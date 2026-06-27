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
    auth_source: str
    username: str | None
    is_superuser: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class UserListRow:
    id: UUID
    oidc_sub: str
    email: str
    name: str
    is_org_admin: bool
    auth_source: str
    username: str | None
    is_superuser: bool
    team_names: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LocalUserCredentials:
    id: UUID
    username: str
    password_hash: str
    is_superuser: bool
    is_org_admin: bool


_USER_SELECT = """
    id, oidc_sub, email, name, is_org_admin,
    auth_source, username, is_superuser, created_at
"""


_USER_LIST_SELECT = """
    u.id, u.oidc_sub, u.email, u.name, u.is_org_admin,
    u.auth_source, u.username, u.is_superuser, u.created_at,
    COALESCE(
        (
            SELECT string_agg(t.name, ', ' ORDER BY t.name)
            FROM team_members tm
            JOIN teams t ON t.id = tm.team_id
            WHERE tm.user_id = u.id
        ),
        ''
    ) AS team_names
"""


class UserRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, user_id: UUID) -> UserRow | None:
        row = await self._conn.fetchrow(
            f"""
            SELECT {_USER_SELECT}
            FROM users WHERE id = $1
            """,
            user_id,
        )
        return _row_to_user(row) if row else None

    async def get_by_oidc_sub(self, oidc_sub: str) -> UserRow | None:
        row = await self._conn.fetchrow(
            f"""
            SELECT {_USER_SELECT}
            FROM users WHERE oidc_sub = $1
            """,
            oidc_sub,
        )
        return _row_to_user(row) if row else None

    async def get_local_by_username(self, username: str) -> LocalUserCredentials | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, username, password_hash, is_superuser, is_org_admin
            FROM users
            WHERE auth_source = 'local'
              AND username = $1
            """,
            username.strip().lower(),
        )
        if row is None or not row["password_hash"]:
            return None
        return LocalUserCredentials(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            is_superuser=row["is_superuser"],
            is_org_admin=row["is_org_admin"],
        )

    async def has_local_superuser(self) -> bool:
        val = await self._conn.fetchval(
            """
            SELECT 1 FROM users
            WHERE auth_source = 'local' AND is_superuser = true
            LIMIT 1
            """
        )
        return val is not None

    async def list_all(self) -> list[UserRow]:
        rows = await self._conn.fetch(
            f"""
            SELECT {_USER_SELECT}
            FROM users
            ORDER BY email ASC
            """
        )
        return [_row_to_user(row) for row in rows]

    async def list_paginated(
        self,
        *,
        search: str,
        limit: int,
        offset: int,
    ) -> list[UserListRow]:
        if search:
            pattern = f"%{search}%"
            rows = await self._conn.fetch(
                f"""
                SELECT {_USER_LIST_SELECT}
                FROM users u
                WHERE u.email ILIKE $1
                   OR u.name ILIKE $1
                   OR COALESCE(u.username, '') ILIKE $1
                ORDER BY u.email ASC
                LIMIT $2 OFFSET $3
                """,
                pattern,
                limit,
                offset,
            )
        else:
            rows = await self._conn.fetch(
                f"""
                SELECT {_USER_LIST_SELECT}
                FROM users u
                ORDER BY u.email ASC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [_row_to_list_user(row) for row in rows]

    async def count(self, *, search: str) -> int:
        if search:
            pattern = f"%{search}%"
            return await self._conn.fetchval(
                """
                SELECT COUNT(*)::int FROM users u
                WHERE u.email ILIKE $1
                   OR u.name ILIKE $1
                   OR COALESCE(u.username, '') ILIKE $1
                """,
                pattern,
            )
        return await self._conn.fetchval("SELECT COUNT(*)::int FROM users")

    async def count_org_admins(self) -> int:
        return await self._conn.fetchval(
            "SELECT COUNT(*)::int FROM users WHERE is_org_admin = true"
        )

    async def create_local_superuser(
        self,
        *,
        username: str,
        password_hash: str,
        email: str,
        name: str,
    ) -> UserRow:
        external_id = f"local:{username}"
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO users (
                oidc_sub, email, name, is_org_admin,
                auth_source, username, password_hash, is_superuser
            )
            VALUES ($1, $2, $3, true, 'local', $4, $5, true)
            RETURNING {_USER_SELECT}
            """,
            external_id,
            email,
            name,
            username,
            password_hash,
        )
        if row is None:
            msg = "failed to create local superuser"
            raise RuntimeError(msg)
        return _row_to_user(row)

    async def upsert_external_user(
        self,
        *,
        external_id: str,
        email: str,
        name: str,
        is_org_admin: bool = False,
    ) -> UserRow:
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO users (oidc_sub, email, name, is_org_admin, auth_source)
            VALUES ($1, $2, $3, $4, 'sso')
            ON CONFLICT (oidc_sub) DO UPDATE
            SET email = EXCLUDED.email,
                name = CASE
                    WHEN EXCLUDED.name <> '' THEN EXCLUDED.name
                    ELSE users.name
                END
            RETURNING {_USER_SELECT}
            """,
            external_id,
            email,
            name,
            is_org_admin,
        )
        if row is None:
            msg = "failed to upsert user"
            raise RuntimeError(msg)
        return _row_to_user(row)

    async def upsert_oidc_user(
        self,
        *,
        oidc_sub: str,
        email: str,
        name: str,
        is_org_admin: bool = False,
    ) -> UserRow:
        return await self.upsert_external_user(
            external_id=oidc_sub,
            email=email,
            name=name,
            is_org_admin=is_org_admin,
        )

    async def set_org_admin(
        self, user_id: UUID, *, is_org_admin: bool
    ) -> UserRow | None:
        row = await self._conn.fetchrow(
            f"""
            UPDATE users SET is_org_admin = $2 WHERE id = $1
            RETURNING {_USER_SELECT}
            """,
            user_id,
            is_org_admin,
        )
        return _row_to_user(row) if row else None


def _row_to_list_user(row: asyncpg.Record) -> UserListRow:
    return UserListRow(
        id=row["id"],
        oidc_sub=row["oidc_sub"],
        email=row["email"],
        name=row["name"],
        is_org_admin=row["is_org_admin"],
        auth_source=row.get("auth_source", "sso"),
        username=row.get("username"),
        is_superuser=row.get("is_superuser", False),
        team_names=row.get("team_names") or "",
        created_at=row["created_at"],
    )


def _row_to_user(row: asyncpg.Record) -> UserRow:
    return UserRow(
        id=row["id"],
        oidc_sub=row["oidc_sub"],
        email=row["email"],
        name=row["name"],
        is_org_admin=row["is_org_admin"],
        auth_source=row.get("auth_source", "sso"),
        username=row.get("username"),
        is_superuser=row.get("is_superuser", False),
        created_at=row["created_at"],
    )
