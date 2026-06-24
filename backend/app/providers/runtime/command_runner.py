"""Run git commands inside a disposable Docker container.

Default image ``alpine/git`` is a minimal (~30MB) image with git pre-installed.
We use it so clone/checkout runs in an isolated container via the Docker Engine
API instead of requiring git on the host or in the worker image.

That image sets ENTRYPOINT to ``git``, so callers pass ``["git", "clone", ...]``
and we forward only the subcommand to the container entrypoint.
"""
import asyncio
import logging
from pathlib import Path

from docker import DockerClient

logger = logging.getLogger(__name__)


class DockerCommandRunner:
    def __init__(
        self,
        client: DockerClient,
        git_image: str,
        workspace_root: Path,
    ) -> None:
        self._client = client
        self._git_image = git_image
        self._workspace_root = workspace_root

    async def run(self, args: list[str], cwd: Path) -> None:
        await asyncio.to_thread(self._run_sync, args, cwd)

    def _run_sync(self, args: list[str], cwd: Path) -> None:
        workspace_root = self._workspace_root.resolve()
        cwd_resolved = cwd.resolve()

        try:
            relative = cwd_resolved.relative_to(workspace_root)
        except ValueError as exc:
            msg = f"cwd {cwd} is outside workspace root {workspace_root}"
            raise RuntimeError(msg) from exc

        workdir = "/workspace"
        if relative.parts:
            workdir = f"/workspace/{relative.as_posix()}"

        volumes = {str(workspace_root): {"bind": "/workspace", "mode": "rw"}}

        run_kwargs: dict = {
            "volumes": volumes,
            "working_dir": workdir,
            "remove": True,
        }
        if args and args[0] == "git":
            run_kwargs["entrypoint"] = ["git"]
            command = args[1:]
        else:
            command = args

        logger.debug(
            "docker run %s %s (workdir=%s)", self._git_image, command, workdir
        )
        try:
            self._client.containers.run(
                self._git_image,
                command=command,
                **run_kwargs,
            )
        except Exception as exc:
            msg = f"docker run failed for {' '.join(args)}: {exc}"
            raise RuntimeError(msg) from exc
