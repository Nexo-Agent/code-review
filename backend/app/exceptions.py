import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(asyncpg.PostgresError)
    async def postgres_error_handler(
        _request: Request, exc: asyncpg.PostgresError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Database error", "type": type(exc).__name__},
        )
