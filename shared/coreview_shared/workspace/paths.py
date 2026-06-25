import re
from pathlib import Path

_UNSAFE_SLUG_CHARS = re.compile(r"[^a-z0-9._-]+")


def safe_repo_slug(repo_full_name: str) -> str:
    """Map owner/repo or org/project/repo to a single filesystem segment."""
    slug = repo_full_name.strip().replace("/", "__").lower()
    slug = _UNSAFE_SLUG_CHARS.sub("-", slug)
    return slug.strip("-") or "unknown"


def repo_base_dir(root: Path, git_provider: str, repo_full_name: str) -> Path:
    provider = git_provider.strip().lower() or "unknown"
    return root / provider / safe_repo_slug(repo_full_name)


def mirror_dir(repo_base: Path) -> Path:
    return repo_base / "mirror"


def worktree_dir(repo_base: Path, pr_number: int, head_sha: str) -> Path:
    sha_prefix = head_sha[:7] if head_sha else "unknown"
    return repo_base / "worktrees" / f"pr-{pr_number}-{sha_prefix}"
