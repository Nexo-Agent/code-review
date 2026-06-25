import logging
import shutil
from pathlib import Path

from coreview_shared.protocols import CommandRunner

logger = logging.getLogger(__name__)


def _git_cmd(auth_args: list[str], *args: str) -> list[str]:
    return ["git", *auth_args, *args]


def is_mirror(path: Path) -> bool:
    return path.is_dir() and (path / "HEAD").is_file()


async def ensure_mirror(
    runner: CommandRunner,
    mirror_path: Path,
    clone_url: str,
    *,
    auth_args: list[str] | None = None,
) -> None:
    auth = auth_args or []
    if is_mirror(mirror_path):
        return

    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    if mirror_path.exists():
        shutil.rmtree(mirror_path)

    await runner.run(
        _git_cmd(auth, "clone", "--bare", clone_url, str(mirror_path)),
        cwd=mirror_path.parent,
    )


async def fetch_mirror(
    runner: CommandRunner,
    mirror_path: Path,
    head_sha: str,
    *,
    auth_args: list[str] | None = None,
) -> None:
    auth = auth_args or []
    await runner.run(
        _git_cmd(auth, "fetch", "origin", head_sha, "--prune"),
        cwd=mirror_path,
    )


def recover_mirror(mirror_path: Path) -> None:
    if mirror_path.exists():
        logger.warning("Removing corrupt mirror at %s", mirror_path)
        shutil.rmtree(mirror_path, ignore_errors=True)
