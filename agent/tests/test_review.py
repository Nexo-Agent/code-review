from app.providers.llm.opencode import OpenCodeLLMProvider
from app.providers.protocols import PRContext, PRMetadata, ReviewFinding
from app.services.review_format import split_findings


def test_opencode_parse_findings_from_json() -> None:
    provider = OpenCodeLLMProvider(
        server_url="http://localhost:4096",
        username="opencode",
        password="",
        agent="code-reviewer",
        model="anthropic/claude-sonnet-4-5",
        timeout_seconds=60,
    )
    data = {
        "findings": [
            {
                "severity": "warning",
                "title": "Missing null check",
                "body": "Variable may be None",
                "file_path": "app/main.py",
                "line_start": 10,
            }
        ]
    }
    findings = provider._parse_findings(data)
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].file_path == "app/main.py"


def test_opencode_slim_prompt_mentions_mcp() -> None:
    provider = OpenCodeLLMProvider(
        server_url="http://localhost:4096",
        username="opencode",
        password="",
        agent="code-reviewer",
        model="test/model",
        timeout_seconds=60,
    )
    context = PRContext(
        metadata=PRMetadata(
            repo_full_name="org/repo",
            pr_number=1,
            title="Test",
            author="dev",
            head_sha="a" * 40,
            base_sha="b" * 40,
            head_ref="feature",
            base_ref="main",
            html_url="https://github.com/org/repo/pull/1",
        ),
        diff="diff content",
    )
    prompt = provider._build_prompt(context)
    assert "coreview-git_fetch_pr_context" in prompt
    assert "diff content" not in prompt


def test_split_findings() -> None:
    findings = [
        ReviewFinding(
            severity="warning",
            title="Bug",
            body="details",
            file_path="a.py",
            line_start=5,
        ),
        ReviewFinding(
            severity="info",
            title="Note",
            body="general",
        ),
    ]
    inline, summary = split_findings(findings)
    assert len(inline) == 1
    assert inline[0].path == "a.py"
    assert len(summary) == 1
    assert summary[0].title == "Note"
