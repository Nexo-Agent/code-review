from app.providers.protocols import ReviewFinding


def format_comment(
    findings: list[ReviewFinding],
    repo_full_name: str,
    pr_number: int,
) -> str:
    if not findings:
        return (
            f"## Code Review — {repo_full_name}#{pr_number}\n\n"
            "No issues found. LGTM!"
        )
    lines = [f"## Code Review — {repo_full_name}#{pr_number}\n"]
    for finding in findings:
        loc = ""
        if finding.file_path:
            loc = f" (`{finding.file_path}`"
            if finding.line_start:
                loc += f":{finding.line_start}"
            loc += ")"
        lines.append(
            f"### [{finding.severity.upper()}] {finding.title}{loc}\n"
            f"{finding.body}\n"
        )
    return "\n".join(lines)
