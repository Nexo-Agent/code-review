from pathlib import Path
from typing import Protocol


class CommandRunner(Protocol):
    async def run(self, args: list[str], cwd: Path) -> None: ...
