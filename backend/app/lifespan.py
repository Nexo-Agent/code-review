from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.config import get_settings
from app.services.integration_settings import (
    get_integration_settings,
    sync_opencode_config,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    async with app.state.pool.acquire() as conn:
        try:
            row = await get_integration_settings(conn)
            sync_opencode_config(row)
        except Exception:
            pass
    yield
    await app.state.pool.close()
