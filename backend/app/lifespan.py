from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.config import get_settings
from app.observability.server import start_metrics_server_if_enabled
from app.services.provider_resolution import sync_opencode_config_from_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    start_metrics_server_if_enabled()
    app.state.pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    async with app.state.pool.acquire() as conn:
        try:
            await sync_opencode_config_from_db(conn)
        except Exception:
            pass
    yield
    await app.state.pool.close()
