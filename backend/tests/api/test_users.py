from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.dependencies import get_conn
from app.main import create_app
from tests.conftest import make_dev_user


@pytest.fixture
async def app_client():
    app = create_app()
    mock_conn = AsyncMock()
    admin = make_dev_user(is_org_admin=True)

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_current_user] = lambda: admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, mock_conn
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_users_paginated(app_client) -> None:
    client, _mock_conn = app_client
    user_id = uuid4()

    with patch(
        "app.api.v1.users.list_users_paginated",
        new_callable=AsyncMock,
    ) as list_users:
        from datetime import UTC, datetime

        from app.schemas.user import UserListItemResponse, UserListResponse

        now = datetime.now(tz=UTC)
        list_users.return_value = UserListResponse(
            items=[
                UserListItemResponse(
                    id=user_id,
                    email="admin@example.com",
                    name="Admin",
                    username="admin",
                    auth_source="local",
                    is_org_admin=True,
                    is_superuser=True,
                    team_names="Default Team",
                    created_at=now,
                )
            ],
            total=1,
        )
        response = await client.get("/api/v1/users?limit=20&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "admin@example.com"


@pytest.mark.asyncio
async def test_list_users_forbidden_for_non_admin() -> None:
    app = create_app()
    mock_conn = AsyncMock()
    member = make_dev_user(is_org_admin=False)

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_current_user] = lambda: member

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/users")

    app.dependency_overrides.clear()
    assert response.status_code == 403
