import logging
import shutil
from pathlib import Path

from coreview_shared.workspace.git_mirror import (
    ensure_mirror,
    fetch_mirror,
    is_mirror,
    recover_mirror,
)
from coreview_shared.workspace.lock import acquire_mirror_lock
from coreview_shared.workspace.paths import worktree_dir
from coreview_shared.workspace.protocol import CommandRunner

logger = logging.getLogger(__name__)

_HEAD_SHA_MARKER = ".nexo-head-sha"


def _git_cmd(auth_args: list[str], *args: str) -> list[str]:
    return ["git", *auth_args, *args]


def _read_marker(worktree_path: Path) -> str | None:
    marker = worktree_path / _HEAD_SHA_MARKER
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8").strip() or None


def _write_marker(worktree_path: Path, head_sha: str) -> None:
    (worktree_path / _HEAD_SHA_MARKER).write_text(head_sha, encoding="utf-8")


def _worktree_ready(worktree_path: Path, head_sha: str) -> bool:
    return (
        worktree_path.is_dir()
        and (worktree_path / ".git").exists()
        and _read_marker(worktree_path) == head_sha
    )


async def ensure_worktree(
    runner: CommandRunner,
    mirror_path: Path,
    repo_base: Path,
    worktree_path: Path,
    head_sha: str,
    *,
    auth_args: list[str] | None = None,
) -> Path:
    auth = auth_args or []
    if not is_mirror(mirror_path):
        msg = f"Git mirror not found at {mirror_path}"
        raise RuntimeError(msg)

    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    with acquire_mirror_lock(repo_base):
        if _worktree_ready(worktree_path, head_sha):
            return worktree_path

        if worktree_path.exists():
            await remove_worktree(runner, mirror_path, worktree_path, auth_args=auth)

        await runner.run(
            _git_cmd(
                auth,
                "worktree",
                "add",
                "-f",
                str(worktree_path),
                head_sha,
            ),
            cwd=mirror_path,
        )
        _write_marker(worktree_path, head_sha)

    return worktree_path


async def prune_stale_worktrees(
    runner: CommandRunner,
    mirror_path: Path,
    repo_base: Path,
    pr_number: int,
    current_head_sha: str,
    *,
    auth_args: list[str] | None = None,
) -> None:
    auth = auth_args or []
    worktrees_root = repo_base / "worktrees"
    if not worktrees_root.is_dir():
        return

    current_name = f"pr-{pr_number}-{current_head_sha[:7]}"
    with acquire_mirror_lock(repo_base):
        for entry in worktrees_root.iterdir():
            if not entry.is_dir():
                continue
            if not entry.name.startswith(f"pr-{pr_number}-"):
                continue
            if entry.name == current_name:
                continue
            logger.info("Pruning stale worktree %s", entry)
            await remove_worktree(runner, mirror_path, entry, auth_args=auth)


async def remove_worktree(
    runner: CommandRunner,
    mirror_path: Path,
    worktree_path: Path,
    *,
    auth_args: list[str] | None = None,
) -> None:
    auth = auth_args or []
    if not worktree_path.exists():
        return

    if is_mirror(mirror_path):
        try:
            await runner.run(
                _git_cmd(auth, "worktree", "remove", "--force", str(worktree_path)),
                cwd=mirror_path,
            )
            return
        except RuntimeError:
            logger.warning(
                "git worktree remove failed for %s; removing directory",
                worktree_path,
            )

    shutil.rmtree(worktree_path, ignore_errors=True)


async def prepare_repo_worktree(
    runner: CommandRunner,
    repo_base: Path,
    mirror_path: Path,
    clone_url: str,
    pr_number: int,
    head_sha: str,
    *,
    auth_args: list[str] | None = None,
) -> Path:
    """Ensure mirror exists, fetch head SHA, prune stale PR worktrees, add worktree."""
    auth = auth_args or []
    repo_base.mkdir(parents=True, exist_ok=True)

    with acquire_mirror_lock(repo_base):
        await ensure_mirror(runner, mirror_path, clone_url, auth_args=auth)
        try:
            await fetch_mirror(runner, mirror_path, head_sha, auth_args=auth)
        except RuntimeError:
            recover_mirror(mirror_path)
            await ensure_mirror(runner, mirror_path, clone_url, auth_args=auth)
            await fetch_mirror(runner, mirror_path, head_sha, auth_args=auth)

    wt_path = worktree_dir(repo_base, pr_number, head_sha)
    await prune_stale_worktrees(
        runner,
        mirror_path,
        repo_base,
        pr_number,
        head_sha,
        auth_args=auth,
    )
    return await ensure_worktree(
        runner,
        mirror_path,
        repo_base,
        wt_path,
        head_sha,
        auth_args=auth,
    )
