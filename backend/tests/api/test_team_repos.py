import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.main import create_app
from app.repositories.teams import DEFAULT_TEAM_ID
from tests.conftest import make_dev_user


@pytest.fixture
async def client_with_db() -> AsyncClient:
    app = create_app()
    dev_user = make_dev_user()

    async def override_get_current_user():
        return dev_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_repo_integration(client_with_db: AsyncClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    create = await client_with_db.post(
        f"/api/v1/teams/{DEFAULT_TEAM_ID}/repos",
        json={
            "name": f"Test Repo {suffix}",
            "git_provider": "github",
            "repo_full_name": f"acme/test-repo-{suffix}",
            "github_webhook_secret": "whsec-test",
            "github_token": "ghp-test",
            "ado_webhook_username": "hook-user",
            "ado_webhook_password": "hook-pass",
            "system_prompt": "Review carefully.",
            "enabled": True,
        },
    )
    assert create.status_code == 201, create.text
    integration_id = create.json()["id"]

    update = await client_with_db.put(
        f"/api/v1/teams/{DEFAULT_TEAM_ID}/repos/{integration_id}",
        json={
            "name": f"Test Repo Renamed {suffix}",
            "system_prompt": "Updated prompt.",
            "ado_webhook_username": "hook-user-updated",
        },
    )
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["name"] == f"Test Repo Renamed {suffix}"
    assert body["system_prompt"] == "Updated prompt."

    delete = await client_with_db.delete(
        f"/api/v1/teams/{DEFAULT_TEAM_ID}/repos/{integration_id}",
    )
    assert delete.status_code == 204
