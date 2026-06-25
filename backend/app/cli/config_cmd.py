from pathlib import Path

import typer

app = typer.Typer(help="Configuration helpers.")


@app.command("render-opencode")
def render_opencode(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to write generated OpenCode config",
    ),
) -> None:
    """Render opencode.json from DB LLM providers."""
    import asyncio

    import asyncpg

    from app.config import get_settings
    from app.paths import opencode_generated_config_path
    from app.services.provider_resolution import sync_opencode_config_from_db

    async def _run() -> Path:
        settings = get_settings()
        conn = await asyncpg.connect(settings.database_url)
        try:
            return await sync_opencode_config_from_db(
                conn, output_path=output or opencode_generated_config_path()
            )
        finally:
            await conn.close()

    path = asyncio.run(_run())
    typer.echo(f"Wrote {path}")
