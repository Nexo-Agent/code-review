from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_db_pool, init_db_pool
from app.observability.server import start_metrics_server_if_enabled
from app.rbac.repositories import PermissionCache
from app.services.provider_resolution import sync_opencode_config_from_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    PermissionCache.invalidate()
    start_metrics_server_if_enabled()
    app.state.pool = await init_db_pool()
    async with app.state.pool.acquire() as conn:
        try:
            await sync_opencode_config_from_db(conn)
        except Exception:
            pass
    yield
    await close_db_pool()
