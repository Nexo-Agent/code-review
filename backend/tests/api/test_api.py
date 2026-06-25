import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def client_with_db() -> AsyncClient:
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_requires_database(client_with_db: AsyncClient) -> None:
    response = await client_with_db.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert "db" in payload
    assert "version" in payload


@pytest.mark.asyncio
async def test_openapi_schema(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Nexo Co-Review API"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/reviews" in schema["paths"]
    assert "/api/v1/webhooks/github" in schema["paths"]
