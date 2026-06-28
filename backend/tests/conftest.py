from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.rbac.catalog import ActionKey, RoleKey
from app.rbac.models import EffectivePermissions, TeamRoleAssignment
from app.repositories.reviews import ReviewRow
from app.repositories.teams import DEFAULT_TEAM_ID
from app.repositories.users import UserRow

ORG_ADMIN_ACTIONS = sorted(a.value for a in ActionKey)
MEMBER_TEAM_ACTIONS = sorted(
    [
        ActionKey.TEAM_READ.value,
        ActionKey.REPO_READ.value,
        ActionKey.REVIEW_READ.value,
        ActionKey.REVIEW_RERUN.value,
        ActionKey.REVIEW_FINDING_READ.value,
    ]
)
VIEWER_TEAM_ACTIONS = sorted(
    [
        ActionKey.TEAM_READ.value,
        ActionKey.REPO_READ.value,
        ActionKey.REVIEW_READ.value,
        ActionKey.REVIEW_FINDING_READ.value,
    ]
)


def make_review_row(**overrides: object) -> ReviewRow:
    now = datetime.now(tz=UTC)
    defaults: dict[str, object] = {
        "id": uuid4(),
        "provider": "github",
        "repo_full_name": "org/repo",
        "pr_number": 42,
        "pr_title": "",
        "pr_url": "",
        "pr_author": "",
        "head_sha": "abc123",
        "base_sha": "",
        "base_ref": "",
        "head_ref": "",
        "status": "pending",
        "delivery_id": None,
        "repo_integration_id": UUID("11111111-1111-1111-1111-111111111111"),
        "team_id": DEFAULT_TEAM_ID,
        "error_message": None,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "summary_comment_posted": False,
        "inline_comments_posted": 0,
        "inline_comments_skipped": 0,
    }
    defaults.update(overrides)
    return ReviewRow(**defaults)  # type: ignore[arg-type]


def make_dev_user(**overrides: object) -> UserRow:
    now = datetime.now(tz=UTC)
    defaults: dict[str, object] = {
        "id": uuid4(),
        "oidc_sub": "test-sub",
        "email": "test@example.com",
        "name": "Test User",
        "is_org_admin": True,
        "auth_source": "sso",
        "username": None,
        "is_superuser": False,
        "created_at": now,
    }
    defaults.update(overrides)
    return UserRow(**defaults)  # type: ignore[arg-type]


def make_effective_permissions(
    user: UserRow,
    accessible_team_ids: list[UUID],
    *,
    team_role: str = RoleKey.MEMBER.value,
) -> EffectivePermissions:
    if user.is_org_admin or user.is_superuser:
        org_roles = [RoleKey.ORG_ADMIN.value]
        org_actions = ORG_ADMIN_ACTIONS
        team_actions = {
            str(team_id): ORG_ADMIN_ACTIONS for team_id in accessible_team_ids
        }
        memberships = [
            TeamRoleAssignment(team_id=team_id, role_key=RoleKey.TEAM_ADMIN.value)
            for team_id in accessible_team_ids
        ]
    else:
        org_roles = [RoleKey.ORG_MEMBER.value]
        org_actions: list[str] = []
        actions = (
            VIEWER_TEAM_ACTIONS
            if team_role == RoleKey.VIEWER.value
            else MEMBER_TEAM_ACTIONS
        )
        team_actions = {str(team_id): actions for team_id in accessible_team_ids}
        memberships = [
            TeamRoleAssignment(team_id=team_id, role_key=team_role)
            for team_id in accessible_team_ids
        ]

    return EffectivePermissions(
        organization_roles=org_roles,
        organization_actions=org_actions,
        team_memberships=memberships,
        team_actions=team_actions,
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a running Postgres database",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("-m") and "integration" in config.getoption("-m"):
        return
    skip_integration = pytest.mark.skip(
        reason="integration tests skipped; run with: pytest -m integration"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
