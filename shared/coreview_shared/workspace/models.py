from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceSpec:
    review_id: str
    repo_full_name: str
    pr_number: int
    head_sha: str


@dataclass(frozen=True, slots=True)
class Workspace:
    path: Path
    spec: WorkspaceSpec


@dataclass(frozen=True, slots=True)
class PreparedWorkspace:
    """Concrete local workspace artifacts produced by the git adapter."""

    repo_base: Path
    mirror_path: Path
    worktree_path: Path
    workspace: Workspace
