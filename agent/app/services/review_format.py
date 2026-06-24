from app.providers.protocols import InlineComment, ReviewFinding


def split_findings(
    findings: list[ReviewFinding],
) -> tuple[list[InlineComment], list[ReviewFinding]]:
    inline: list[InlineComment] = []
    summary_only: list[ReviewFinding] = []
    for finding in findings:
        if finding.file_path and finding.line_start:
            body = f"**[{finding.severity.upper()}] {finding.title}**\n\n{finding.body}"
            inline.append(
                InlineComment(
                    path=finding.file_path,
                    line=finding.line_start,
                    body=body,
                )
            )
        else:
            summary_only.append(finding)
    return inline, summary_only


def format_summary_comment(
    findings: list[ReviewFinding],
    repo_full_name: str,
    pr_number: int,
) -> str:
    if not findings:
        return (
            f"## Nexo Co-Review — {repo_full_name}#{pr_number}\n\n"
            "No issues found. LGTM!"
        )
    lines = [f"## Nexo Co-Review — {repo_full_name}#{pr_number}\n"]
    for finding in findings:
        loc = ""
        if finding.file_path:
            loc = f" (`{finding.file_path}`"
            if finding.line_start:
                loc += f":{finding.line_start}"
            loc += ")"
        lines.append(
            f"### [{finding.severity.upper()}] {finding.title}{loc}\n{finding.body}\n"
        )
    return "\n".join(lines)
