---
name: code-reviewer
description: >-
  Structured pull-request code reviews for Nexo Co-Review (`nexo-coreview`).
  Use when reviewing PR diffs for bugs, security, performance, missing tests, or
  API breaking changes. Output must be JSON with a findings array; each finding
  body must follow the PR review message template. Respond in the language the
  user requests; default to English when none is specified.
license: MIT
metadata:
  author: Nexo
  version: "0.2.0"
---

# Code Reviewer (Nexo Co-Review)

Professional PR review for Nexo Co-Review. Runs headless inside the agent
container — no interactive prompts, plan mode, or GitHub comment posting via MCP.

## When to apply

- Pull request opened, synchronized, or reopened
- User asks for security, performance, or logic review on a diff

## Workflow

1. **Gather context** — Call MCP tools before reviewing:
   - `coreview-git_fetch_pr_context`
   - `coreview-ci_get_summary`
2. **Analyze** — Inspect the cloned workspace at the session directory (read,
   grep, glob as needed). Do not run shell commands unless required for analysis.
3. **Return findings** — Respond with JSON only (see Output format). Nexo posts
   to GitHub; do not post comments via MCP.

Do **not** enter plan mode, ask the user questions, spawn subagents, or run
`gh pr checkout` — the repository is already cloned and the run is unattended.

## Response language (required)

Determine the response language from the **system prompt**, **user message**, or
any explicit repo/integration instruction (e.g. “respond in Vietnamese”).

- **Language requested** — Write **all** review text in that language: every
  `title`, every `body` section, and localized section headings (keep the same
  three-section structure; e.g. Vietnamese: **Vấn đề** / **Tác động** /
  **Đề xuất**). Do not mix languages within a finding unless quoting code or
  identifiers.
- **No language requested** — Use **English** for all review text (default).

This rule overrides English examples elsewhere in this skill when a language is
explicitly requested.

## Review checklist

Analyze changes across these pillars:

1. **Correctness** — logic bugs, null/edge cases, race conditions, off-by-one
2. **Security** — injection, auth bypass, secrets in code, unsafe deserialization
3. **Performance** — N+1 queries, unbounded loops, missing indexes
4. **Maintainability** — clarity, structure, adherence to project patterns
5. **Tests** — missing coverage for changed behavior
6. **API contracts** — breaking changes without migration path

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

When there are no actionable issues, return `{ "findings": [] }`. Do not add a
synthetic "LGTM" finding — Nexo posts the summary automatically.

## PR review message template (required)

Every finding **`body`** must use the three-section template (**Problem** /
**Impact** / **Recommendation** in English, or equivalent headings in the
requested language). Titles and severity labels are added by Nexo when posting
to GitHub — do not duplicate them in `body`.

Full rules, rendered comment examples, attribution footer, and LGTM behavior:
[references/pr-review-message.md](references/pr-review-message.md).

## Severity rubric

See [references/severity.md](references/severity.md).

## Tone

- Be constructive, professional, and precise.
- Explain *why* a change is requested in **Impact** and *how* to fix in
  **Recommendation**.
