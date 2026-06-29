from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PRMetadata:
    repo_full_name: str
    pr_number: int
    title: str
    author: str
    head_sha: str
    base_sha: str
    head_ref: str
    base_ref: str
    html_url: str


@dataclass(frozen=True, slots=True)
class PRContext:
    metadata: PRMetadata
    diff: str
    ci_summary: str = ""


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    severity: str
    title: str
    body: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
