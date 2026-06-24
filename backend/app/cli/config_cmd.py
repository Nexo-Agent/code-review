from pathlib import Path

import typer

app = typer.Typer(help="Configuration helpers.")


@app.command("render-opencode")
def render_opencode(
    output: Path = typer.Option(
        Path("opencode.generated.json"),
        "--output",
        "-o",
        help="Path to write generated OpenCode config",
    ),
) -> None:
    """Render opencode.json from DB integration settings (or env bootstrap)."""
    import asyncio

    import asyncpg

    from app.config import get_settings
    from app.services.integration_settings import (
        get_integration_settings,
        sync_opencode_config,
    )

    async def _run() -> Path:
        settings = get_settings()
        conn = await asyncpg.connect(settings.database_url)
        try:
            row = await get_integration_settings(conn)
            return sync_opencode_config(row, output_path=output)
        finally:
            await conn.close()

    path = asyncio.run(_run())
    typer.echo(f"Wrote {path}")
