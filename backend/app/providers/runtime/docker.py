import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

from app.providers.protocols import Workspace, WorkspaceSpec

logger = logging.getLogger(__name__)


class DockerRuntimeProvider:
    def __init__(
        self,
        workspace_root: str,
        github_token: str,
        workspace_image: str | None = None,
    ) -> None:
        self._workspace_root = Path(workspace_root)
        self._github_token = github_token
        self._workspace_image = workspace_image

    async def prepare_workspace(self, spec: WorkspaceSpec) -> Workspace:
        return await asyncio.to_thread(self._prepare_workspace_sync, spec)

    async def cleanup_workspace(self, workspace: Workspace) -> None:
        await asyncio.to_thread(self._cleanup_sync, workspace.path)

    def _prepare_workspace_sync(self, spec: WorkspaceSpec) -> Workspace:
        path = self._workspace_root / spec.review_id
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

        clone_url = (
            f"https://x-access-token:{self._github_token}"
            f"@github.com/{spec.repo_full_name}.git"
        )
        self._run_git(["clone", "--depth", "1", clone_url, str(path / "repo")])
        repo_path = path / "repo"
        self._run_git(
            ["fetch", "origin", spec.head_sha],
            cwd=repo_path,
        )
        self._run_git(
            ["checkout", spec.head_sha],
            cwd=repo_path,
        )
        return Workspace(path=repo_path, spec=spec)

    def _cleanup_sync(self, path: Path) -> None:
        parent = path.parent if path.name == "repo" else path
        if parent.exists() and parent.is_dir():
            shutil.rmtree(parent, ignore_errors=True)

    def _run_git(self, args: list[str], cwd: Path | None = None) -> None:
        if self._workspace_image:
            volume = str(cwd or self._workspace_root)
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volume}:/workspace",
                "-w",
                "/workspace",
                self._workspace_image,
                "git",
                *args,
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return

        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            msg = f"git {' '.join(args)} failed: {result.stderr}"
            raise RuntimeError(msg)
