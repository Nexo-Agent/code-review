import asyncio
import logging
import sys
from uuid import UUID

import typer

from app.services.review_runner import execute_review_logic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,
)

app = typer.Typer(help="Run PR code reviews inside the agent container.")


@app.command("run")
def run(
    review_id: UUID = typer.Option(..., help="Review UUID to process"),
) -> None:
    """Execute a single review job (worktree checkout, LLM review, post findings)."""
    asyncio.run(execute_review_logic(str(review_id)))
    typer.echo(f"Review {review_id} completed.")
