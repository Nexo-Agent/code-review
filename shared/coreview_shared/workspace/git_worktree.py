import logging
import shutil
from pathlib import Path

from coreview_shared.workspace.git_executor import LocalGitExecutor
from coreview_shared.workspace.git_mirror import MirrorOperator
from coreview_shared.workspace.lock import WorkspaceLock
from coreview_shared.workspace.paths import worktree_dir

logger = logging.getLogger(__name__)

_HEAD_SHA_MARKER = ".nexo-head-sha"


class WorktreeOperator:
    """Create, prune, and remove review worktrees backed by a shared mirror.

    Worktrees are materialized per review head revision so the review pipeline
    can operate on an isolated checkout while still reusing the repository's
    shared bare mirror. This operator coordinates mirror freshness, stale
    worktree cleanup, and safe worktree mutations under a repository lock.
    """

    def __init__(
        self,
        *,
        git_executor: LocalGitExecutor | None = None,
        mirror_operator: MirrorOperator | None = None,
        workspace_lock: WorkspaceLock | None = None,
    ) -> None:
        """Initialize the operator with its mirror and locking collaborators."""

        resolved_git_executor = git_executor or LocalGitExecutor()
        self._git_executor = resolved_git_executor
        self._mirror_operator = mirror_operator or MirrorOperator(
            git_executor=resolved_git_executor
        )
        self._workspace_lock = workspace_lock or WorkspaceLock()

    async def ensure_worktree(
        self,
        mirror_path: Path,
        repo_base: Path,
        worktree_path: Path,
        head_sha: str,
        *,
        auth_args: list[str] | None = None,
    ) -> Path:
        """Ensure a worktree exists at ``head_sha`` and is ready for review.

        The method reuses an existing worktree when it already matches the
        expected head revision. Otherwise it removes the stale directory and
        recreates the worktree from the shared mirror.
        """

        auth = auth_args or []
        if not self._mirror_operator.is_mirror(mirror_path):
            msg = f"Git mirror not found at {mirror_path}"
            raise RuntimeError(msg)

        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        with self._workspace_lock.acquire(repo_base):
            if self._worktree_ready(worktree_path, head_sha):
                return worktree_path

            if worktree_path.exists():
                await self.remove_worktree(
                    mirror_path,
                    worktree_path,
                    auth_args=auth,
                )

            await self._git_executor.run(
                self._git_cmd(
                    auth,
                    "worktree",
                    "add",
                    "-f",
                    str(worktree_path),
                    head_sha,
                ),
                cwd=mirror_path,
            )
            self._write_marker(worktree_path, head_sha)

        return worktree_path

    async def prune_stale_worktrees(
        self,
        mirror_path: Path,
        repo_base: Path,
        pr_number: int,
        current_head_sha: str,
        *,
        auth_args: list[str] | None = None,
    ) -> None:
        """Remove older worktrees for the same review number.

        Keeping only the current worktree per pull request avoids accumulating
        stale directories when a branch is updated repeatedly across review
        runs.
        """

        auth = auth_args or []
        worktrees_root = repo_base / "worktrees"
        if not worktrees_root.is_dir():
            return

        current_name = f"pr-{pr_number}-{current_head_sha[:7]}"
        with self._workspace_lock.acquire(repo_base):
            for entry in worktrees_root.iterdir():
                if not entry.is_dir():
                    continue
                if not entry.name.startswith(f"pr-{pr_number}-"):
                    continue
                if entry.name == current_name:
                    continue
                logger.info("Pruning stale worktree %s", entry)
                await self.remove_worktree(
                    mirror_path,
                    entry,
                    auth_args=auth,
                )

    async def remove_worktree(
        self,
        mirror_path: Path,
        worktree_path: Path,
        *,
        auth_args: list[str] | None = None,
    ) -> None:
        """Remove a worktree, falling back to directory deletion if needed."""

        auth = auth_args or []
        if not worktree_path.exists():
            return

        if self._mirror_operator.is_mirror(mirror_path):
            try:
                await self._git_executor.run(
                    self._git_cmd(
                        auth,
                        "worktree",
                        "remove",
                        "--force",
                        str(worktree_path),
                    ),
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
        self,
        repo_base: Path,
        mirror_path: Path,
        clone_url: str,
        pr_number: int,
        head_sha: str,
        *,
        auth_args: list[str] | None = None,
    ) -> Path:
        """Prepare a fresh review worktree from the shared repository mirror.

        This method guarantees the repository base exists, ensures the mirror is
        available, fetches the desired head revision, recovers from mirror
        corruption by recloning when needed, prunes stale worktrees for the same
        pull request, and finally materializes the target worktree.
        """

        auth = auth_args or []
        repo_base.mkdir(parents=True, exist_ok=True)

        with self._workspace_lock.acquire(repo_base):
            await self._mirror_operator.ensure_mirror(
                mirror_path,
                clone_url,
                auth_args=auth,
            )
            try:
                await self._mirror_operator.fetch_mirror(
                    mirror_path,
                    head_sha,
                    auth_args=auth,
                )
            except RuntimeError:
                self._mirror_operator.recover_mirror(mirror_path)
                await self._mirror_operator.ensure_mirror(
                    mirror_path,
                    clone_url,
                    auth_args=auth,
                )
                await self._mirror_operator.fetch_mirror(
                    mirror_path,
                    head_sha,
                    auth_args=auth,
                )

        wt_path = worktree_dir(repo_base, pr_number, head_sha)
        await self.prune_stale_worktrees(
            mirror_path,
            repo_base,
            pr_number,
            head_sha,
            auth_args=auth,
        )
        return await self.ensure_worktree(
            mirror_path,
            repo_base,
            wt_path,
            head_sha,
            auth_args=auth,
        )

    def _read_marker(self, worktree_path: Path) -> str | None:
        marker = worktree_path / _HEAD_SHA_MARKER
        if not marker.is_file():
            return None
        return marker.read_text(encoding="utf-8").strip() or None

    def _write_marker(self, worktree_path: Path, head_sha: str) -> None:
        (worktree_path / _HEAD_SHA_MARKER).write_text(head_sha, encoding="utf-8")

    def _worktree_ready(self, worktree_path: Path, head_sha: str) -> bool:
        return (
            worktree_path.is_dir()
            and (worktree_path / ".git").exists()
            and self._read_marker(worktree_path) == head_sha
        )

    def _git_cmd(self, auth_args: list[str], *args: str) -> list[str]:
        return ["git", *auth_args, *args]
