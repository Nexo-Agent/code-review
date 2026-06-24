import typer

from app.cli import backend, config_cmd, job

app = typer.Typer(
    name="code-review",
    help="Nexo Co-Review (nexo-coreview) — backend API and Celery worker.",
    no_args_is_help=True,
)

app.add_typer(backend.app, name="backend")
app.add_typer(job.app, name="job")
app.add_typer(config_cmd.app, name="config")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
