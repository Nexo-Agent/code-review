# Review And Findings

## Review lifecycle

A review represents one analysis run for one repository change revision.

In practice, the uniqueness boundary is:

- repository full name
- PR or MR number
- head SHA

The system creates a new review when a new revision is received, and it may create another review for the same PR if the head SHA changes or the user explicitly retries.

## Review statuses

Current review states stored in the database:

- `pending`
- `running`
- `completed`
- `failed`

### State transitions

- webhook creation creates a `pending` review
- agent callback `review.started` sets the review to `running`
- agent callback `review.completed` sets the review to `completed`
- agent callback `review.failed` sets the review to `failed`

## Review metadata

A review stores both queueing information and PR or MR metadata.

Important fields:

- provider
- repo_full_name
- pr_number
- pr_title
- pr_url
- pr_author
- head_sha
- base_sha
- head_ref
- base_ref
- delivery_id
- team_id
- repo_integration_id
- timestamps

Some metadata is available at webhook time, and the rest is enriched when the agent starts and resolves provider metadata.

## Review creation sources

Reviews can be created from:

- inbound Git provider webhooks
- manual retry from the review detail UI or API

Retries create a fresh review run instead of mutating the old run in place.

## Findings model

Each review may produce zero or more findings.

A finding stores:

- severity
- file path
- start line
- end line
- title
- body

Current severity values expected from OpenCode:

- `critical`
- `warning`
- `info`
- `suggestion`

## Finding generation path

1. the agent runs OpenCode against the prepared review workspace
2. OpenCode returns structured JSON findings
3. the agent splits findings into inline-comment candidates and summary-only findings
4. inline comments are posted to the Git provider when possible
5. the remaining findings are included in the summary comment
6. all normalized findings are sent back to the backend callback endpoint

## Inline versus summary behavior

The system distinguishes two delivery channels:

### Inline comments

Used when the finding can be attached to a valid line in the current diff.

### Summary comment

Used for:

- findings without a valid inline location
- findings intentionally kept out of inline review
- the overall review summary

The review record stores delivery stats:

- `summary_comment_posted`
- `inline_comments_posted`
- `inline_comments_skipped`

## Persistence behavior

The backend replaces the stored findings for the completed review run when it receives `review.completed`.

This means one completed run has one authoritative set of findings in the database.

## Access model

Reviews are team-scoped through `reviews.team_id`.

Access to list, read, and retry reviews is controlled by RBAC actions such as:

- `review.read`
- `review.rerun`
- `review.finding.read`

## UI presentation

The current frontend exposes review information in two main places:

### Review list

Shows:

- PR number
- title
- repository
- status
- last run time

### Review detail

Shows:

- review metadata
- findings with severity filters
- findings grouped by file or shown as a flat list
- previous runs for the same PR
- delivery stats for summary and inline comments

## Review deduplication

During webhook ingestion, the backend avoids duplicate runs by checking:

- provider delivery id when available
- existing review with the same repo, PR, and head SHA

This prevents the same provider event from spawning repeated work.

## Current limitations visible in code

- findings are text-first and do not include richer semantic taxonomies
- analytics over findings are not yet a separate subsystem
- review history exists at the run level, not as a separate “review thread” aggregate
