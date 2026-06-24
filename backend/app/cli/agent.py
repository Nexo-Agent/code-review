"""Standalone agent runner (debug/local)."""

import asyncio
from uuid import UUID

import typer

from app.services.review_runner import execute_review_logic

app = typer.Typer(help="Standalone agent runner (debug/local).")


@app.command("run")
def run(
    review_id: UUID = typer.Option(..., help="Review UUID to process"),
) -> None:
    """Run a single review job inline (no Celery)."""
    asyncio.run(execute_review_logic(str(review_id)))
    typer.echo(f"Review {review_id} completed.")
