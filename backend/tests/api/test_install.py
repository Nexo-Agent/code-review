from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_conn
from app.main import create_app
from tests.conftest import make_dev_user


@pytest.fixture
async def app_client():
    app = create_app()
    mock_conn = AsyncMock()

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield app, client, mock_conn
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_install_status(app_client) -> None:
    _app, client, _mock_conn = app_client

    with patch(
        "app.api.v1.install.get_install_status",
        new_callable=AsyncMock,
    ) as get_status:
        get_status.return_value = {"setup_required": True}
        response = await client.get("/api/v1/install/status")

    assert response.status_code == 200
    assert response.json()["setup_required"] is True


@pytest.mark.asyncio
async def test_install_bootstrap_blocked_after_setup(app_client) -> None:
    _app, client, _mock_conn = app_client

    from app.services.install import SetupAlreadyCompletedError

    with patch(
        "app.api.v1.install.bootstrap_install",
        new_callable=AsyncMock,
    ) as bootstrap:
        bootstrap.side_effect = SetupAlreadyCompletedError()
        response = await client.post(
            "/api/v1/install/bootstrap",
            json={
                "username": "admin",
                "password": "super-secure-pass",
            },
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_local_login_invalid_credentials(app_client) -> None:
    _app, client, _mock_conn = app_client

    with patch(
        "app.api.v1.auth.authenticate_local_user",
        new_callable=AsyncMock,
    ) as auth_local:
        auth_local.return_value = None
        response = await client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "wrong-password"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_local_login_success(app_client) -> None:
    _app, client, _mock_conn = app_client
    user = make_dev_user(
        username="admin",
        auth_source="local",
        is_superuser=True,
    )

    with (
        patch(
            "app.api.v1.auth.authenticate_local_user",
            new_callable=AsyncMock,
        ) as auth_local,
        patch(
            "app.api.v1.auth.create_session",
            new_callable=AsyncMock,
        ) as create_session,
        patch(
            "app.api.v1.auth.get_accessible_team_ids",
            new_callable=AsyncMock,
        ) as team_ids,
    ):
        auth_local.return_value = user
        create_session.return_value = "session-token"
        team_ids.return_value = []
        response = await client.post(
            "/api/v1/auth/local/login",
            json={"username": "admin", "password": "super-secure-pass"},
        )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == user.email
    assert "cogito_session" in response.headers.get("set-cookie", "")
