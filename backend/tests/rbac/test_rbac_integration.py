import pytest

from app.rbac.catalog import ActionKey
from app.rbac.checker import PermissionChecker, PermissionDeniedError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_viewer_cannot_rerun_review(db_conn, viewer_user, team_id) -> None:
    checker = PermissionChecker(db_conn)
    with pytest.raises(PermissionDeniedError):
        await checker.require(
            viewer_user,
            ActionKey.REVIEW_RERUN,
            team_id=team_id,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_can_rerun_review(db_conn, member_user, team_id) -> None:
    checker = PermissionChecker(db_conn)
    decision = await checker.require(
        member_user,
        ActionKey.REVIEW_RERUN,
        team_id=team_id,
    )
    assert decision.allowed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_viewer_cannot_create_repo(db_conn, viewer_user, team_id) -> None:
    checker = PermissionChecker(db_conn)
    with pytest.raises(PermissionDeniedError):
        await checker.require(
            viewer_user,
            ActionKey.REPO_CREATE,
            team_id=team_id,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_org_admin_can_manage_settings(db_conn, org_admin_user) -> None:
    checker = PermissionChecker(db_conn)
    decision = await checker.require(org_admin_user, ActionKey.SETTINGS_SSO_UPDATE)
    assert decision.allowed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_org_member_cannot_manage_settings(db_conn, org_member_user) -> None:
    checker = PermissionChecker(db_conn)
    with pytest.raises(PermissionDeniedError):
        await checker.require(org_member_user, ActionKey.SETTINGS_SSO_UPDATE)
