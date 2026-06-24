---
name: code-review
description: >-
  Perform structured pull-request code reviews. Use when reviewing PR diffs,
  checking for bugs, security issues, performance problems, missing tests, or
  API breaking changes. Output must be JSON with findings array.
license: MIT
metadata:
  author: Nexo
  version: "0.1.0"
---

# Nexo Co-Review

Structured PR review for Nexo Co-Review (`nexo-coreview`).

## When to apply

- Pull request opened, synchronized, or reopened
- User asks for security, performance, or logic review on a diff

## Review checklist

1. **Logic bugs** — null/edge cases, race conditions, off-by-one errors
2. **Security** — injection, auth bypass, secrets in code, unsafe deserialization
3. **Performance** — N+1 queries, unbounded loops, missing indexes
4. **Tests** — missing coverage for changed behavior
5. **API contracts** — breaking changes without migration path

## Output format (required)

Return JSON:

```json
{
  "findings": [
    {
      "severity": "critical|warning|info|suggestion",
      "title": "Short title",
      "body": "Detailed explanation and recommendation",
      "file_path": "path/to/file.py",
      "line_start": 42,
      "line_end": 45
    }
  ]
}
```

## Severity rubric

See [references/severity.md](references/severity.md).
