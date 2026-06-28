from uuid import UUID, uuid4

import pytest_asyncio

from app.rbac.catalog import RoleKey
from app.rbac.repositories import RbacRepository
from app.repositories.team_members import TeamMemberRepository
from app.repositories.users import UserRepository

DEFAULT_TEAM_ID = UUID("00000000-0000-4000-8000-000000000002")


@pytest_asyncio.fixture
async def org_admin_user(db_conn):
    row = await UserRepository(db_conn).upsert_oidc_user(
        oidc_sub=f"org-admin-{uuid4()}",
        email=f"org-admin-{uuid4()}@test.com",
        name="Org Admin",
        is_org_admin=True,
    )
    await RbacRepository(db_conn).set_organization_role(row.id, RoleKey.ORG_ADMIN)
    refreshed = await UserRepository(db_conn).get(row.id)
    assert refreshed is not None
    return refreshed


@pytest_asyncio.fixture
async def org_member_user(db_conn):
    row = await UserRepository(db_conn).upsert_oidc_user(
        oidc_sub=f"org-member-{uuid4()}",
        email=f"org-member-{uuid4()}@test.com",
        name="Org Member",
        is_org_admin=False,
    )
    await RbacRepository(db_conn).set_organization_role(row.id, RoleKey.ORG_MEMBER)
    refreshed = await UserRepository(db_conn).get(row.id)
    assert refreshed is not None
    return refreshed


@pytest_asyncio.fixture
async def team_id(db_conn):
    return DEFAULT_TEAM_ID


async def _add_team_member(db_conn, user_id: UUID, role: str) -> None:
    await TeamMemberRepository(db_conn).add(
        team_id=DEFAULT_TEAM_ID,
        user_id=user_id,
        role=role,
    )


@pytest_asyncio.fixture
async def viewer_user(db_conn, org_member_user):
    await _add_team_member(db_conn, org_member_user.id, RoleKey.VIEWER.value)
    return org_member_user


@pytest_asyncio.fixture
async def member_user(db_conn, org_member_user):
    user = await UserRepository(db_conn).upsert_oidc_user(
        oidc_sub=f"member-{uuid4()}",
        email=f"member-{uuid4()}@test.com",
        name="Member",
        is_org_admin=False,
    )
    await RbacRepository(db_conn).set_organization_role(user.id, RoleKey.ORG_MEMBER)
    await _add_team_member(db_conn, user.id, RoleKey.MEMBER.value)
    refreshed = await UserRepository(db_conn).get(user.id)
    assert refreshed is not None
    return refreshed
