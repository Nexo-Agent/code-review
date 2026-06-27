import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.main import create_app
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
async def test_update_llm_provider(client_with_db: AsyncClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    create = await client_with_db.post(
        "/api/v1/settings/llm-providers",
        json={
            "name": f"Test Provider {suffix}",
            "provider_id": f"openai-compat-{suffix}",
            "base_url": "https://llm.example.com/v1",
            "model": "test-model",
            "is_default": False,
        },
    )
    assert create.status_code == 201
    provider_id = create.json()["id"]

    update = await client_with_db.put(
        f"/api/v1/settings/llm-providers/{provider_id}",
        json={"name": f"Test Provider Renamed {suffix}"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == f"Test Provider Renamed {suffix}"

    delete = await client_with_db.delete(
        f"/api/v1/settings/llm-providers/{provider_id}",
    )
    assert delete.status_code == 204
