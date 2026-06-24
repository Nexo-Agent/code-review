import typer

from app.cli import agent, backend, config_cmd, job, mcp

app = typer.Typer(
    name="code-review",
    help="Nexo Co-Review (nexo-coreview) — backend API, Celery worker, or agent runner.",
    no_args_is_help=True,
)

app.add_typer(backend.app, name="backend")
app.add_typer(job.app, name="job")
app.add_typer(agent.app, name="agent")
app.add_typer(config_cmd.app, name="config")
app.add_typer(mcp.app, name="mcp")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
