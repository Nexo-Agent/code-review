from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from coreview_shared.workspace.diff_builder import DiffBuilder
from coreview_shared.workspace.git_executor import LocalGitExecutor
from coreview_shared.workspace.git_mirror import MirrorOperator
from coreview_shared.workspace.git_worktree import WorktreeOperator
from coreview_shared.workspace.lock import WorkspaceLock
from coreview_shared.workspace.models import PreparedWorkspace, Workspace, WorkspaceSpec
from coreview_shared.workspace.paths import mirror_dir

if TYPE_CHECKING:
    from coreview_shared.git.models import RemoteRepoAccess


class GitWorkspace:
    """Coordinate local Git workspace preparation for review execution.

    This class is the high-level entry point used by Git providers. It composes
    specialized collaborators for mirror management, worktree lifecycle,
    repository locking, and diff generation so provider implementations only
    supply remote access details and review metadata.
    """

    def __init__(
        self,
        *,
        git_executor: LocalGitExecutor | None = None,
        mirror_operator: MirrorOperator | None = None,
        worktree_operator: WorktreeOperator | None = None,
        workspace_lock: WorkspaceLock | None = None,
        diff_builder: DiffBuilder | None = None,
    ) -> None:
        """Initialize the workspace manager and its composed collaborators.

        Args:
            git_executor: Local Git executor used for mirror and worktree
                commands inside the agent runtime.
            mirror_operator: Operator responsible for maintaining the shared
                bare mirror. A default instance is created when omitted.
            worktree_operator: Operator responsible for worktree lifecycle. When
                omitted, a default operator is created with the same mirror
                operator and lock instance used by this workspace.
            workspace_lock: Lock implementation used to serialize mirror and
                worktree mutations per repository.
            diff_builder: Component used to generate local unified diffs.
        """

        resolved_git_executor = git_executor or LocalGitExecutor()
        resolved_lock = workspace_lock or WorkspaceLock()
        resolved_mirror_operator = mirror_operator or MirrorOperator(
            git_executor=resolved_git_executor
        )
        self._mirror_operator = resolved_mirror_operator
        self._workspace_lock = resolved_lock
        self._worktree_operator = worktree_operator or WorktreeOperator(
            git_executor=resolved_git_executor,
            mirror_operator=resolved_mirror_operator,
            workspace_lock=resolved_lock,
        )
        self._diff_builder = diff_builder or DiffBuilder()

    async def prepare_workspace(
        self,
        spec: WorkspaceSpec,
        repo_base: Path,
        access: RemoteRepoAccess,
    ) -> PreparedWorkspace:
        """Prepare a review-local worktree and return its concrete artifacts.

        Args:
            spec: Normalized review workspace request metadata.
            repo_base: Root path for the repository's shared mirror and
                worktrees.
            access: Remote repository access details such as clone URL and auth
                arguments.

        Returns:
            A ``PreparedWorkspace`` describing the mirror, worktree, and
            review-facing workspace path.
        """

        mirror_path = mirror_dir(repo_base)
        worktree_path = await self._worktree_operator.prepare_repo_worktree(
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
        """Build the review diff from the prepared local worktree."""

        return await self._diff_builder.build_diff(
            prepared_workspace,
            base_sha=base_sha,
            head_sha=head_sha,
        )

    async def cleanup_workspace(
        self,
        prepared_workspace: PreparedWorkspace,
        access: RemoteRepoAccess,
    ) -> None:
        """Remove the prepared worktree once review execution is complete."""

        await self._worktree_operator.remove_worktree(
            prepared_workspace.mirror_path,
            prepared_workspace.worktree_path,
            auth_args=list(access.auth_args),
        )
