from datetime import UTC, datetime

from coreview_shared.protocols import InlineComment
from coreview_shared.providers.git.diff_lines import (
    filter_inline_comments,
    parse_commentable_lines,
)
from coreview_shared.schemas.review_callback import (
    ReviewCallbackAgent,
    ReviewCallbackEvent,
    ReviewCallbackRequest,
)


def test_parse_commentable_lines() -> None:
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,3 +1,4 @@
 line1
-line2
+line2changed
 line3
+line4
"""
    lines = parse_commentable_lines(diff)
    assert ("a.py", 2, "LEFT") in lines
    assert ("a.py", 2, "RIGHT") in lines
    assert ("a.py", 4, "RIGHT") in lines


def test_filter_inline_comments() -> None:
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 x
+y
"""
    comments = [
        InlineComment(path="a.py", line=2, body="ok"),
        InlineComment(path="a.py", line=99, body="bad"),
    ]
    valid, skipped = filter_inline_comments(comments, diff)
    assert len(valid) == 1
    assert valid[0].line == 2
    assert len(skipped) == 1
    assert skipped[0].line == 99


def test_review_callback_event_roundtrip() -> None:
    event = ReviewCallbackEvent(
        event="review.started",
        review_id="550e8400-e29b-41d4-a716-446655440000",
        occurred_at=datetime.now(tz=UTC),
        agent=ReviewCallbackAgent(name="coreview-agent", version="0.1.0"),
        request=ReviewCallbackRequest(
            git_provider="github",
            repo_full_name="org/repo",
            pr_number=1,
            head_sha="abc123",
        ),
    )
    payload = event.model_dump_json()
    restored = ReviewCallbackEvent.model_validate_json(payload)
    assert restored.event == "review.started"
    assert restored.request.repo_full_name == "org/repo"
