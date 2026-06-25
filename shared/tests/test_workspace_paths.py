from pathlib import Path

from coreview_shared.workspace.paths import (
    mirror_dir,
    repo_base_dir,
    safe_repo_slug,
    worktree_dir,
)


def test_safe_repo_slug_github() -> None:
    assert safe_repo_slug("Nexo-Agent/Code-Review") == "nexo-agent__code-review"


def test_safe_repo_slug_ado() -> None:
    assert safe_repo_slug("fabrikam/MyProject/Repo") == "fabrikam__myproject__repo"


def test_repo_base_dir() -> None:
    root = Path("/workspaces")
    base = repo_base_dir(root, "github", "org/repo")
    assert base == Path("/workspaces/github/org__repo")


def test_mirror_and_worktree_dirs() -> None:
    base = Path("/workspaces/github/org__repo")
    assert mirror_dir(base) == base / "mirror"
    assert worktree_dir(base, 42, "deadbeef0123456789") == (
        base / "worktrees" / "pr-42-deadbee"
    )
