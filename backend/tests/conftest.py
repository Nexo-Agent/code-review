from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.repositories.projects import DEFAULT_PROJECT_ID
from app.repositories.reviews import ReviewRow
from app.repositories.teams import DEFAULT_TEAM_ID
from app.repositories.users import UserRow


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
        "project_id": DEFAULT_PROJECT_ID,
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
