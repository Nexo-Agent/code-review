import fcntl
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def acquire_mirror_lock(
    repo_base: Path,
    *,
    timeout: float = 300.0,
    poll_interval: float = 0.2,
) -> Iterator[None]:
    """Exclusive lock for mirror fetch and worktree mutations on a repo base."""
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
