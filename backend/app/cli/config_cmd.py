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
    from app.services.provider_resolution import sync_opencode_config_from_db

    async def _run() -> Path:
        settings = get_settings()
        conn = await asyncpg.connect(settings.database_url)
        try:
            return await sync_opencode_config_from_db(conn, output_path=output)
        finally:
            await conn.close()

    path = asyncio.run(_run())
    typer.echo(f"Wrote {path}")
