from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from coreview_shared.workspace.git_mirror import ensure_mirror, is_mirror
from coreview_shared.workspace.git_worktree import (
    prepare_repo_worktree,
    remove_worktree,
)
from coreview_shared.workspace.paths import mirror_dir, worktree_dir


@pytest.mark.asyncio
async def test_ensure_mirror_clones_when_missing(tmp_path: Path) -> None:
    runner = AsyncMock()
    mirror = tmp_path / "mirror"
    await ensure_mirror(runner, mirror, "https://example.com/repo.git")
    runner.run.assert_awaited_once()
    args = runner.run.await_args_list[0].args[0]
    assert args[:4] == ["git", "clone", "--bare", "https://example.com/repo.git"]


@pytest.mark.asyncio
async def test_ensure_mirror_skips_when_exists(tmp_path: Path) -> None:
    runner = AsyncMock()
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    (mirror / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    assert is_mirror(mirror)
    await ensure_mirror(runner, mirror, "https://example.com/repo.git")
    runner.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_repo_worktree_invokes_fetch_and_worktree(
    tmp_path: Path,
) -> None:
    repo_base = tmp_path / "github" / "org__repo"
    mirror = mirror_dir(repo_base)
    mirror.mkdir(parents=True)
    (mirror / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    head_sha = "deadbeef0123456789deadbeef0123456789"
    expected_wt = worktree_dir(repo_base, 7, head_sha)

    async def fake_run(args: list[str], cwd: Path) -> None:
        if args[1:3] == ["worktree", "add"]:
            Path(args[4]).mkdir(parents=True, exist_ok=True)
            (Path(args[4]) / ".git").write_text("gitdir: ../mirror\n", encoding="utf-8")

    runner = AsyncMock()
    runner.run.side_effect = fake_run

    wt = await prepare_repo_worktree(
        runner,
        repo_base,
        mirror,
        "https://example.com/org/repo.git",
        pr_number=7,
        head_sha=head_sha,
    )
    assert wt == expected_wt

    commands = [call.args[0] for call in runner.run.await_args_list]
    assert any(cmd[1:3] == ["fetch", "origin"] for cmd in commands)
    assert any(cmd[1:3] == ["worktree", "add"] for cmd in commands)


@pytest.mark.asyncio
async def test_remove_worktree_rmtree_when_not_mirror(tmp_path: Path) -> None:
    runner = AsyncMock()
    wt = tmp_path / "worktree"
    wt.mkdir()
    (wt / "file.txt").write_text("x", encoding="utf-8")
    await remove_worktree(runner, tmp_path / "missing-mirror", wt)
    assert not wt.exists()
