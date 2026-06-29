import asyncio
import subprocess
from pathlib import Path


class LocalGitExecutor:
    """Run local Git commands inside the agent runtime.

    Workspace preparation is owned entirely by the agent, so Git commands no
    longer need an abstract cross-runtime command runner. This executor wraps
    local process execution and provides one concrete place for Git invocation
    and error translation.
    """

    async def run(self, args: list[str], cwd: Path) -> None:
        """Execute a Git command in ``cwd`` and raise on failure."""

        await asyncio.to_thread(self._run_sync, args, cwd)

    def _run_sync(self, args: list[str], cwd: Path) -> None:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
        output = result.stderr or result.stdout or ""
        msg = f"Command failed ({result.returncode}): {' '.join(args)}\n{output}"
        raise RuntimeError(msg)
