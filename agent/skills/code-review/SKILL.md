---
name: code-review
description: >-
  Perform structured pull-request code reviews. Use when reviewing PR diffs,
  checking for bugs, security issues, performance problems, missing tests, or
  API breaking changes. Output must be JSON with findings array; each finding
  body must follow the PR review message template.
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

Return JSON only (no free-form markdown outside JSON):

```json
{
  "findings": [
    {
      "severity": "critical|warning|info|suggestion",
      "title": "Short imperative title (≤ 80 chars, no period)",
      "body": "**Problem:** ...\n\n**Impact:** ...\n\n**Recommendation:** ...",
      "file_path": "path/to/file.py",
      "line_start": 42,
      "line_end": 45
    }
  ]
}
```

## PR review message template (required)

Every finding **`body`** must use the three-section template (**Problem** / **Impact** / **Recommendation**). Titles and severity labels are added by Nexo when posting to GitHub — do not duplicate them in `body`.

Full rules, rendered comment examples, attribution footer, and LGTM behavior: [references/pr-review-message.md](references/pr-review-message.md).

## Severity rubric

See [references/severity.md](references/severity.md).
