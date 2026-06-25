import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client_with_db() -> AsyncClient:
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_llm_provider(client_with_db: AsyncClient) -> None:
    create = await client_with_db.post(
        "/api/v1/settings/llm-providers",
        json={
            "name": "Test Provider",
            "provider_id": "openai-compat",
            "base_url": "https://llm.example.com/v1",
            "model": "test-model",
            "is_default": False,
        },
    )
    assert create.status_code == 201
    provider_id = create.json()["id"]

    update = await client_with_db.put(
        f"/api/v1/settings/llm-providers/{provider_id}",
        json={"name": "Test Provider Renamed"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Test Provider Renamed"

    delete = await client_with_db.delete(
        f"/api/v1/settings/llm-providers/{provider_id}",
    )
    assert delete.status_code == 204
