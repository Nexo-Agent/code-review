import logging
import re
from uuid import UUID

from app.repositories.organizations import OrganizationRepository
from app.repositories.team_members import TeamMemberRepository
from app.repositories.teams import TeamRepository, TeamRow
from app.repositories.users import UserRepository
from app.schemas.team import (
    TeamCreate,
    TeamListResponse,
    TeamMemberCreate,
    TeamMemberListResponse,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
)

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "team"


def _unique_slug(base: str, existing: set[str]) -> str:
    slug = base
    index = 2
    while slug in existing:
        slug = f"{base}-{index}"
        index += 1
    return slug


def to_team_response(
    row: TeamRow,
    *,
    repo_count: int = 0,
    member_count: int = 0,
) -> TeamResponse:
    return TeamResponse(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        slug=row.slug,
        repo_count=repo_count,
        member_count=member_count,
        created_at=row.created_at,
    )


async def list_teams(conn, *, user) -> list[TeamResponse]:
    result = await list_teams_paginated(conn, user=user, search="", limit=100, offset=0)
    return result.items


async def list_teams_paginated(
    conn,
    *,
    user,
    search: str | None,
    limit: int,
    offset: int,
) -> TeamListResponse:
    from app.rbac.effective_permissions import get_accessible_team_ids_from_permissions

    repo = TeamRepository(conn)
    query = (search or "").strip()
    accessible = await get_accessible_team_ids_from_permissions(conn, user)
    if not accessible:
        return TeamListResponse(items=[], total=0)
    rows = await repo.list_paginated_for_teams(
        team_ids=accessible,
        search=query,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_for_teams(team_ids=accessible, search=query)
    team_ids = [row.id for row in rows]
    repo_counts = await repo.count_repos_for_teams(team_ids)
    member_counts = await TeamMemberRepository(conn).count_members_for_teams(team_ids)
    return TeamListResponse(
        items=[
            to_team_response(
                row,
                repo_count=repo_counts.get(row.id, 0),
                member_count=member_counts.get(row.id, 0),
            )
            for row in rows
        ],
        total=total,
    )


async def create_team(conn, payload: TeamCreate) -> TeamResponse:
    org = await OrganizationRepository(conn).get_default()
    if org is None:
        msg = "organization not configured"
        raise ValueError(msg)
    repo = TeamRepository(conn)
    if payload.slug:
        slug = payload.slug
    else:
        existing = {row.slug for row in await repo.list_all(organization_id=org.id)}
        slug = _unique_slug(_slugify(payload.name), existing)
    row = await repo.create(
        organization_id=org.id,
        name=payload.name,
        slug=slug,
    )
    logger.info("Created team %s", row.slug)
    return to_team_response(row)


async def update_team(conn, team_id: UUID, payload: TeamUpdate) -> TeamResponse:
    row = await TeamRepository(conn).update(
        team_id,
        name=payload.name,
    )
    if row is None:
        msg = "team not found"
        raise ValueError(msg)
    return to_team_response(row)


async def delete_team(conn, team_id: UUID) -> None:
    await TeamRepository(conn).delete(team_id)


async def list_team_members(conn, team_id: UUID) -> list[TeamMemberResponse]:
    result = await list_team_members_paginated(
        conn, team_id, search="", limit=100, offset=0
    )
    return result.items


async def list_team_members_paginated(
    conn,
    team_id: UUID,
    *,
    search: str | None,
    limit: int,
    offset: int,
) -> TeamMemberListResponse:
    repo = TeamMemberRepository(conn)
    query = (search or "").strip()
    rows = await repo.list_for_team_paginated(
        team_id,
        search=query,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_for_team(team_id, search=query)
    return TeamMemberListResponse(
        items=[
            TeamMemberResponse(
                team_id=row.team_id,
                user_id=row.user_id,
                role=row.role,
                user_email=row.user_email,
                user_name=row.user_name,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
    )


async def add_team_member(
    conn,
    team_id: UUID,
    payload: TeamMemberCreate,
) -> TeamMemberResponse:
    user = await UserRepository(conn).get(payload.user_id)
    if user is None:
        msg = "user not found"
        raise ValueError(msg)
    row = await TeamMemberRepository(conn).add(
        team_id=team_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    return TeamMemberResponse(
        team_id=row.team_id,
        user_id=row.user_id,
        role=row.role,
        user_email=row.user_email,
        user_name=row.user_name,
        created_at=row.created_at,
    )


async def remove_team_member(conn, team_id: UUID, user_id: UUID) -> None:
    await TeamMemberRepository(conn).remove(team_id, user_id)


async def list_users(conn) -> list:
    from app.schemas.auth import UserResponse

    rows = await UserRepository(conn).list_all()
    return [
        UserResponse(
            id=row.id,
            email=row.email,
            name=row.name,
            is_org_admin=row.is_org_admin,
            created_at=row.created_at,
        )
        for row in rows
    ]
