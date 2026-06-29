import logging
import shutil
from pathlib import Path

from coreview_shared.workspace.git_executor import LocalGitExecutor

logger = logging.getLogger(__name__)


class MirrorOperator:
    """Manage the shared bare Git mirror for a repository workspace.

    Each repository keeps one reusable bare clone under its repo base directory.
    Review-specific worktrees are created from that mirror so repeated reviews
    avoid full clones. This operator owns mirror creation, fetch updates, and
    recovery when the local mirror becomes unusable.
    """

    def __init__(
        self,
        *,
        git_executor: LocalGitExecutor | None = None,
    ) -> None:
        """Initialize the operator with the local Git executor."""

        self._git_executor = git_executor or LocalGitExecutor()

    def is_mirror(self, path: Path) -> bool:
        """Return whether ``path`` looks like a valid bare Git mirror."""

        return path.is_dir() and (path / "HEAD").is_file()

    async def ensure_mirror(
        self,
        mirror_path: Path,
        clone_url: str,
        *,
        auth_args: list[str] | None = None,
    ) -> None:
        """Create the bare mirror when it does not already exist.

        Args:
            mirror_path: Filesystem location where the mirror should live.
            clone_url: Remote clone URL for the repository.
            auth_args: Extra Git command arguments needed for authentication.
        """

        auth = auth_args or []
        if self.is_mirror(mirror_path):
            return

        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        if mirror_path.exists():
            shutil.rmtree(mirror_path)

        await self._git_executor.run(
            self._git_cmd(auth, "clone", "--bare", clone_url, str(mirror_path)),
            cwd=mirror_path.parent,
        )

    async def fetch_mirror(
        self,
        mirror_path: Path,
        head_sha: str,
        *,
        auth_args: list[str] | None = None,
    ) -> None:
        """Fetch the requested head revision into the existing mirror."""

        auth = auth_args or []
        await self._git_executor.run(
            self._git_cmd(auth, "fetch", "origin", head_sha, "--prune"),
            cwd=mirror_path,
        )

    def recover_mirror(self, mirror_path: Path) -> None:
        """Remove a corrupt mirror so it can be recreated from scratch."""

        if mirror_path.exists():
            logger.warning("Removing corrupt mirror at %s", mirror_path)
            shutil.rmtree(mirror_path, ignore_errors=True)

    def _git_cmd(self, auth_args: list[str], *args: str) -> list[str]:
        return ["git", *auth_args, *args]
