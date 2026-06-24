import os

import typer
import uvicorn

app = typer.Typer(help="Run the FastAPI backend.")


@app.command("run")
def run(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(
        int(os.environ.get("APP_PORT", "8000")),
        help="Bind port",
    ),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
) -> None:
    """Start the Code Review API server."""
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        factory=False,
    )
