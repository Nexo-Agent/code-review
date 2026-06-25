import asyncio
import subprocess
from pathlib import Path


class LocalCommandRunner:
    async def run(self, args: list[str], cwd: Path) -> None:
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
