from collections.abc import AsyncGenerator

import asyncpg
from fastapi import Request


async def get_conn(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    async with request.app.state.pool.acquire() as conn:
        yield conn
