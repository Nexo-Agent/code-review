import typer

app = typer.Typer(help="Celery job worker commands.")


@app.command("worker")
def worker(
    loglevel: str = typer.Option("info", help="Celery log level"),
    concurrency: int = typer.Option(1, help="Worker concurrency"),
) -> None:
    """Start the Celery worker for review jobs."""
    from app.jobs.celery_app import celery_app

    celery_app.worker_main(
        argv=[
            "worker",
            f"--loglevel={loglevel}",
            f"--concurrency={concurrency}",
        ]
    )
