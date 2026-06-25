import re

_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_commentable_lines(diff: str) -> set[tuple[str, int, str]]:
    """Lines GitHub accepts for pull request review comments.

    Inline comments must target a line that appears in the PR diff hunks.
    Returns (path, line_number, side) where side is LEFT or RIGHT.
    """
    result: set[tuple[str, int, str]] = set()
    current_path: str | None = None
    new_line = 0
    old_line = 0

    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            parts = raw.split()
            if len(parts) >= 4 and parts[3].startswith("b/"):
                current_path = parts[3][2:]
            continue
        if raw.startswith("+++ b/"):
            current_path = raw[6:]
            continue
        if raw.startswith("--- a/") or not current_path:
            continue

        hunk = _HUNK_HEADER.match(raw)
        if hunk:
            old_line = int(hunk.group(1))
            new_line = int(hunk.group(3))
            continue
        if raw.startswith("\\"):
            continue

        if raw.startswith("+"):
            result.add((current_path, new_line, "RIGHT"))
            new_line += 1
        elif raw.startswith("-"):
            result.add((current_path, old_line, "LEFT"))
            old_line += 1
        elif raw.startswith(" "):
            result.add((current_path, new_line, "RIGHT"))
            result.add((current_path, old_line, "LEFT"))
            new_line += 1
            old_line += 1

    return result


def _normalize_path(path: str) -> str:
    return path.removeprefix("./")


def is_commentable(
    path: str,
    line: int,
    side: str,
    commentable: set[tuple[str, int, str]],
) -> bool:
    normalized = _normalize_path(path)
    return (path, line, side) in commentable or (normalized, line, side) in commentable


def filter_inline_comments(
    comments: list,
    diff: str,
) -> tuple[list, list]:
    """Split comments into postable vs skipped (line not in PR diff)."""
    commentable = parse_commentable_lines(diff)
    valid: list = []
    skipped: list = []
    for comment in comments:
        if is_commentable(comment.path, comment.line, comment.side, commentable):
            valid.append(comment)
        else:
            skipped.append(comment)
    return valid, skipped
