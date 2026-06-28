import pytest

from app.rbac.catalog import ActionKey, RoleKey, ScopeKey
from app.rbac.repositories import is_allowed


@pytest.fixture
def default_matrix() -> dict[tuple[str, str, str], bool]:
    matrix: dict[tuple[str, str, str], bool] = {}

    all_actions = list(ActionKey)
    all_scopes = list(ScopeKey)

    for action in all_actions:
        for scope in all_scopes:
            matrix[(RoleKey.ORG_ADMIN.value, action.value, scope.value)] = True

    team_admin_actions = [
        ActionKey.TEAM_READ,
        ActionKey.TEAM_UPDATE,
        ActionKey.TEAM_MEMBER_READ,
        ActionKey.TEAM_MEMBER_ADD,
        ActionKey.TEAM_MEMBER_UPDATE_ROLE,
        ActionKey.TEAM_MEMBER_REMOVE,
        ActionKey.REPO_READ,
        ActionKey.REPO_CREATE,
        ActionKey.REPO_UPDATE,
        ActionKey.REPO_DELETE,
        ActionKey.REPO_CONFIGURE_CREDENTIALS,
        ActionKey.REVIEW_READ,
        ActionKey.REVIEW_RERUN,
        ActionKey.REVIEW_FINDING_READ,
    ]
    for action in team_admin_actions:
        matrix[(RoleKey.TEAM_ADMIN.value, action.value, ScopeKey.TEAM.value)] = True

    member_actions = [
        ActionKey.TEAM_READ,
        ActionKey.REPO_READ,
        ActionKey.REVIEW_READ,
        ActionKey.REVIEW_RERUN,
        ActionKey.REVIEW_FINDING_READ,
    ]
    for action in member_actions:
        matrix[(RoleKey.MEMBER.value, action.value, ScopeKey.TEAM.value)] = True

    viewer_actions = [
        ActionKey.TEAM_READ,
        ActionKey.REPO_READ,
        ActionKey.REVIEW_READ,
        ActionKey.REVIEW_FINDING_READ,
    ]
    for action in viewer_actions:
        matrix[(RoleKey.VIEWER.value, action.value, ScopeKey.TEAM.value)] = True

    return matrix


def test_org_admin_has_all_permissions(default_matrix: dict) -> None:
    assert is_allowed(
        default_matrix,
        role_key=RoleKey.ORG_ADMIN.value,
        action=ActionKey.SETTINGS_SSO_UPDATE,
        scope=ScopeKey.SETTINGS,
    )
    assert is_allowed(
        default_matrix,
        role_key=RoleKey.ORG_ADMIN.value,
        action=ActionKey.REVIEW_RERUN,
        scope=ScopeKey.TEAM,
    )


def test_viewer_cannot_rerun(default_matrix: dict) -> None:
    assert not is_allowed(
        default_matrix,
        role_key=RoleKey.VIEWER.value,
        action=ActionKey.REVIEW_RERUN,
        scope=ScopeKey.TEAM,
    )


def test_member_can_rerun(default_matrix: dict) -> None:
    assert is_allowed(
        default_matrix,
        role_key=RoleKey.MEMBER.value,
        action=ActionKey.REVIEW_RERUN,
        scope=ScopeKey.TEAM,
    )


def test_viewer_cannot_create_repo(default_matrix: dict) -> None:
    assert not is_allowed(
        default_matrix,
        role_key=RoleKey.VIEWER.value,
        action=ActionKey.REPO_CREATE,
        scope=ScopeKey.TEAM,
    )


def test_team_admin_can_manage_members(default_matrix: dict) -> None:
    assert is_allowed(
        default_matrix,
        role_key=RoleKey.TEAM_ADMIN.value,
        action=ActionKey.TEAM_MEMBER_ADD,
        scope=ScopeKey.TEAM,
    )


def test_unknown_permission_denied(default_matrix: dict) -> None:
    assert not is_allowed(
        default_matrix,
        role_key=RoleKey.ORG_MEMBER.value,
        action=ActionKey.TEAM_DELETE,
        scope=ScopeKey.ORGANIZATION,
    )
