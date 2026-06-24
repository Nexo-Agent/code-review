import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import asyncpg

from app.config import get_settings

T = TypeVar("T")


async def with_connection(
    callback: Coroutine[Any, Any, T],
) -> T:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        return await callback
    finally:
        await conn.close()


async def _run_with_conn(fn: Any, *args: Any, **kwargs: Any) -> Any:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        return await fn(conn, *args, **kwargs)
    finally:
        await conn.close()


def run_db(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)
