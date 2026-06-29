import fcntl
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class WorkspaceLock:
    """Coordinate exclusive filesystem access for a repository workspace.

    The workspace package reuses a shared bare mirror for each repository and
    mutates worktrees beneath the same repo base directory. Those operations are
    not safe to run concurrently across multiple processes without a shared
    synchronization primitive. This class provides a lightweight file lock so
    mirror fetches, recovery, and worktree mutations happen one at a time per
    repository.
    """

    @contextmanager
    def acquire(
        self,
        repo_base: Path,
        *,
        timeout: float = 300.0,
        poll_interval: float = 0.2,
    ) -> Iterator[None]:
        """Acquire an exclusive lock for the given repository base directory.

        Args:
            repo_base: Root directory that owns the mirror and worktrees for one
                repository.
            timeout: Maximum time in seconds to wait for the lock before
                raising ``TimeoutError``.
            poll_interval: Sleep interval in seconds between non-blocking lock
                attempts.

        Yields:
            ``None`` while the caller holds the exclusive lock.

        Raises:
            TimeoutError: If the lock cannot be acquired before ``timeout``.
        """

        repo_base.mkdir(parents=True, exist_ok=True)
        lock_path = repo_base / ".mirror.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        msg = f"Timed out acquiring mirror lock for {repo_base}"
                        raise TimeoutError(msg) from None
                    time.sleep(poll_interval)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
