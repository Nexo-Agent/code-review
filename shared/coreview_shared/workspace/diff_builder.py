import asyncio
import subprocess

from coreview_shared.workspace.models import PreparedWorkspace


class DiffBuilder:
    """Build Git diffs from a prepared local review workspace.

    Review providers normalize remote metadata differently, but once the target
    code is available in a local worktree the system prefers to generate diffs
    through Git itself. That keeps the downstream review flow consistent across
    Git hosting platforms and avoids depending on provider-specific diff APIs.
    """

    async def build_diff(
        self,
        prepared_workspace: PreparedWorkspace,
        *,
        base_sha: str,
        head_sha: str,
    ) -> str:
        """Return a unified diff between two revisions in the prepared worktree.

        Args:
            prepared_workspace: Local workspace artifacts created for the review.
            base_sha: Base revision used as the diff starting point.
            head_sha: Head revision used as the diff end point.

        Returns:
            The unified diff text produced by ``git diff``.

        Raises:
            RuntimeError: If ``git diff`` exits with a non-zero status.
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
