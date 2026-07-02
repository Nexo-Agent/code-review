import asyncio
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import asyncpg

from app.config import get_settings

T = TypeVar("T")
_db_pool: asyncpg.Pool | None = None


async def init_db_pool() -> asyncpg.Pool:
    global _db_pool
    if _db_pool is None:
        settings = get_settings()
        _db_pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )
    return _db_pool


def get_db_pool() -> asyncpg.Pool:
    if _db_pool is None:
        msg = "Database pool is not initialized"
        raise RuntimeError(msg)
    return _db_pool


async def close_db_pool() -> None:
    global _db_pool
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None


@asynccontextmanager
async def acquire_connection():
    pool = get_db_pool()
    async with pool.acquire() as conn:
        yield conn


async def with_connection(
    callback: Coroutine[Any, Any, T],
) -> T:
    async with acquire_connection():
        return await callback


async def run_with_connection(fn: Any, *args: Any, **kwargs: Any) -> Any:
    async with acquire_connection() as conn:
        return await fn(conn, *args, **kwargs)


_worker_event_loop: asyncio.AbstractEventLoop | None = None


def _get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """Reuse one event loop per process for Celery sync tasks.

    ``asyncio.run()`` creates and closes a loop on every call, which breaks
    module-level asyncpg pools initialized on a prior loop.
    """
    global _worker_event_loop
    if _worker_event_loop is None or _worker_event_loop.is_closed():
        _worker_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_event_loop)
    return _worker_event_loop


def run_db(coro: Coroutine[Any, Any, T]) -> T:
    return _get_worker_event_loop().run_until_complete(coro)


def run_db_fn(fn: Any, *args: Any, **kwargs: Any) -> Any:
    return run_db(run_with_connection(fn, *args, **kwargs))
