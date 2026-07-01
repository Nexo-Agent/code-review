from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_code_review_settings, get_settings
from app.exceptions import register_exception_handlers
from app.lifespan import lifespan
from app.observability.middleware import PrometheusMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Cogito Review API",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    if get_code_review_settings().metrics_enabled:
        app.add_middleware(PrometheusMiddleware)
    app.include_router(api_router)

    static_dir = Path(settings.static_dir)
    if (static_dir / "assets").is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=static_dir / "assets"),
            name="assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        index = static_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="SPA index.html not found")

    return app


app = create_app()
