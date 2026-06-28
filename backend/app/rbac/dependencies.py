from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.dependencies import get_conn
from app.rbac.catalog import ActionKey
from app.rbac.checker import PermissionChecker, PermissionDeniedError
from app.repositories.repo_integrations import RepoIntegrationRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.users import UserRow


def _permission_denied() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied",
    )


async def require_org_action(
    action: ActionKey,
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserRow:
    checker = PermissionChecker(conn)
    try:
        await checker.require(user, action)
    except PermissionDeniedError:
        raise _permission_denied()
    return user


def require_org_action_dep(action: ActionKey):
    async def _dep(
        user: UserRow = Depends(get_current_user),
        conn: asyncpg.Connection = Depends(get_conn),
    ) -> UserRow:
        return await require_org_action(action, user=user, conn=conn)

    return _dep


async def require_action_on_team(
    team_id: UUID,
    action: ActionKey,
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserRow:
    checker = PermissionChecker(conn)
    try:
        await checker.require(user, action, team_id=team_id)
    except PermissionDeniedError:
        raise _permission_denied()
    return user


def require_action_on_team_dep(team_id: UUID, action: ActionKey):
    async def _dep(
        user: UserRow = Depends(get_current_user),
        conn: asyncpg.Connection = Depends(get_conn),
    ) -> UserRow:
        return await require_action_on_team(team_id, action, user=user, conn=conn)

    return _dep


async def require_action_on_review(
    review_id: UUID,
    action: ActionKey,
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserRow:
    review = await ReviewRepository(conn).get(review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    checker = PermissionChecker(conn)
    try:
        await checker.require(user, action, team_id=review.team_id)
    except PermissionDeniedError:
        raise _permission_denied()
    return user


async def require_action_on_repo(
    repo_id: UUID,
    action: ActionKey,
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserRow:
    repo = await RepoIntegrationRepository(conn).get(repo_id)
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    checker = PermissionChecker(conn)
    try:
        await checker.require(user, action, team_id=repo.team_id)
    except PermissionDeniedError:
        raise _permission_denied()
    return user


__all__ = [
    "require_action_on_repo",
    "require_action_on_review",
    "require_action_on_team",
    "require_action_on_team_dep",
    "require_org_action",
    "require_org_action_dep",
]
