import asyncio
import subprocess
from pathlib import Path

from coreview_shared.protocols import (
    CommandRunner,
    PreparedWorkspace,
    RemoteRepoAccess,
    Workspace,
    WorkspaceSpec,
)
from coreview_shared.workspace.git_worktree import (
    prepare_repo_worktree,
    remove_worktree,
)
from coreview_shared.workspace.paths import mirror_dir


class GitWorkspaceAdapter:
    """Shared local git workflow used by every git provider implementation.

    Providers should supply only remote access data such as clone URL and git
    auth arguments. This adapter owns the local-first behavior: mirror
    management, worktree checkout, diff generation, and cleanup. Keeping that
    logic here makes all providers behave consistently once code is available in
    the local workspace.
    """

    async def prepare_workspace(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
        runner: CommandRunner,
        access: RemoteRepoAccess,
    ) -> PreparedWorkspace:
        mirror_path = mirror_dir(repo_base)
        worktree_path = await prepare_repo_worktree(
            runner,
            repo_base,
            mirror_path,
            access.clone_url,
            spec.pr_number,
            spec.head_sha,
            auth_args=list(access.auth_args),
        )
        workspace = Workspace(path=worktree_path, spec=spec)
        return PreparedWorkspace(
            repo_base=repo_base,
            mirror_path=mirror_path,
            worktree_path=worktree_path,
            workspace=workspace,
        )

    async def build_diff(
        self,
        prepared_workspace: PreparedWorkspace,
        *,
        base_sha: str,
        head_sha: str,
    ) -> str:
        """Build a unified diff from the local worktree.

        Review providers should prefer this method whenever local checkout is
        available. Remote diff APIs are best treated as fallbacks for platforms
        that cannot faithfully reproduce the review diff via local git.
        """

        def _run_diff() -> str:
            result = subprocess.run(
                ["git", "diff", f"{base_sha}..{head_sha}"],
                cwd=prepared_workspace.worktree_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                output = result.stderr or result.stdout or ""
                msg = f"git diff failed ({result.returncode}): {output}"
                raise RuntimeError(msg)
            return result.stdout

        return await asyncio.to_thread(_run_diff)

    async def cleanup_workspace(
        self,
        prepared_workspace: PreparedWorkspace,
        runner: CommandRunner,
        access: RemoteRepoAccess,
    ) -> None:
        await remove_worktree(
            runner,
            prepared_workspace.mirror_path,
            prepared_workspace.worktree_path,
            auth_args=list(access.auth_args),
        )
