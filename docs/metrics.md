# Metrics

## Purpose

This document defines the core product metrics used to measure the
effectiveness of AI review in the software development workflow.

The scope of this document is intentionally limited to effectiveness metrics.
It does not cover operational reliability metrics such as failure rate,
execution latency, queue time, or infrastructure stability.

The goal is to answer three product questions:

1. does AI review help pull requests move faster
2. are AI comments useful enough that developers act on them
3. is AI review broadly adopted in the code review workflow

## Measurement principles

The metrics in this document follow these principles:

- prefer workflow outcomes over raw activity counts
- measure developer response, not only AI output volume
- compare AI-reviewed and non-AI-reviewed pull requests where possible
- segment by repository, team, and pull request size before drawing conclusions

Raw counts alone are not enough.
For example, more AI comments per pull request does not automatically mean more
value. High comment volume with low helpful feedback may indicate noise rather
than usefulness.

## Core metric set

The current recommended effectiveness dashboard is built around six metrics:

1. PR Time to Merge
2. Time from Review-Ready to Merge
3. Time to First Human Reply
4. Helpful Rate of AI Comments
5. Applied or Fixed Findings Rate
6. AI Review Coverage

## Metric catalog

| Metric | What it measures | How to measure | Insight it provides | Why it matters | Required data | Interpretation notes |
| --- | --- | --- | --- | --- | --- | --- |
| **PR Time to Merge** | Total elapsed time from PR creation to merge for AI-reviewed PRs, and ideally compared against non-AI-reviewed PRs | `merged_at - pr_opened_at` | Shows whether AI review is associated with faster delivery from code submission to merge | This is the closest high-level outcome metric for development flow efficiency | `pr_opened_at`, `merged_at`, PR identifier, flag indicating whether AI review ran | Always segment by PR size, repository, and team. Large or risky PRs may naturally take longer and can distort comparisons |
| **Time from Review-Ready to Merge** | Time spent after a PR is ready for review until merge | `merged_at - review_ready_at` where `review_ready_at` is the moment the PR leaves draft state or is explicitly marked ready | Removes noise from PRs that were opened early but not actually reviewable yet | Gives a cleaner view of review workflow efficiency than total PR lifetime | `review_ready_at`, `merged_at`, PR identifier, AI review presence | If draft state is not available in every provider, define a fallback rule and keep it consistent across providers |
| **Time to First Human Reply** | How long it takes for a human to reply on an AI comment thread after the PR becomes reviewable | `first_human_reply_at - earliest_ai_comment_at` | Indicates whether AI review helps teams engage with feedback sooner | Early reply delay is a major bottleneck in many review cycles | `earliest_ai_comment_at`, `first_human_reply_at`, PR identifier, AI review presence | Counts direct thread replies only, not formal review approvals |
| **Helpful Rate of AI Comments** | Share of AI comments that developers explicitly rate as helpful | `helpful_ai_comments / rated_ai_comments` | Measures explicit developer trust in AI feedback | High usage without trust is weak adoption. This metric reveals whether the feedback is considered useful by the developer who reviewed it | Comment-level AI identifier, feedback events such as `helpful` and `not_helpful`, and denominator event rules | If user feedback is optional, also track rating coverage so the team knows whether the rate is statistically meaningful |
| **Applied or Fixed Findings Rate** | Share of AI findings that lead to an observed fix before merge | `fixed_ai_findings / actionable_ai_findings` | Shows whether AI review produces findings that change code, not only comments that are seen | This is one of the strongest signals that AI review creates practical value | Finding identifier, finding status, code change or resolution event, merge boundary | A finding may be valid but intentionally deferred. Consider separate states such as `fixed`, `dismissed`, `deferred` |
| **AI Review Coverage** | Share of pull requests that actually receive AI review | `ai_reviewed_prs / total_eligible_prs` | Shows how much of the workflow is influenced by AI review | Without coverage, impact metrics are hard to generalize because the sample may be too narrow | Total eligible PR count, AI-reviewed PR count, eligibility rules | Define eligibility clearly. Exclude drafts, bots, or repositories where AI review is intentionally disabled if needed |

## Metric details

### 1. PR Time to Merge

**Definition**

The total time from pull request creation to merge completion.

**Formula**

```text
PR Time to Merge = merged_at - pr_opened_at
```

**Primary insight**

This metric answers the top-level question: does AI review help teams merge
changes faster?

**Why product teams use it**

Products in engineering intelligence and AI review frequently use merge time as
the main workflow outcome metric because it is simple, legible, and closely
connected to delivery speed.

**Important caveats**

- compare AI-reviewed and non-AI-reviewed PRs
- segment by PR size and repository
- do not interpret a single aggregate median without context

### 2. Time from Review-Ready to Merge

**Definition**

The time between a pull request becoming reviewable and its merge.

**Formula**

```text
Time from Review-Ready to Merge = merged_at - review_ready_at
```

**Primary insight**

This metric isolates the portion of the lifecycle most affected by review
behavior.

**Why product teams use it**

Many teams open draft pull requests early. Measuring from PR creation can mix
implementation time with review time and make the impact of AI review harder to
see.

**Important caveats**

- draft-to-ready transitions must be captured consistently
- if provider support differs, document the fallback behavior

### 3. Time to First Human Reply

**Definition**

The elapsed time from review-ready state to the first human reply on an AI review
comment thread.

**Formula**

```text
Time to First Human Reply = first_human_reply_at - earliest_ai_comment_at
```

**Primary insight**

This metric shows whether AI review helps reduce the waiting time before a
person engages with the AI feedback thread.

**Why product teams use it**

In many teams, the first response delay is a major bottleneck. Shortening this
delay usually improves the whole review cycle.

**Important caveats**

- counts direct replies on AI comment threads only
- does not measure formal review approval or reviewer vote events
- do not mix bot activity with human activity

### 4. Helpful Rate of AI Comments

**Definition**

The share of AI comments that developers explicitly rate as helpful.

This metric is based on explicit user feedback only.
The system should not infer helpfulness from code changes, comment reactions in
external providers, or other indirect behavior when calculating this metric.

**Formula**

```text
Helpful Rate = helpful_ai_comments / rated_ai_comments
```

**Primary insight**

This metric measures trust and usefulness, not just visibility.

**Why product teams use it**

AI review systems often generate many comments. The key question is whether
developers find them useful enough to endorse or act on.

For this metric, endorsement means a direct reply on the AI comment thread with
one of the supported keywords: `Helpful` or `Not Helpful` (case-insensitive,
exact match after normalization).

**Important caveats**

- feedback only works when the developer replies directly on the AI comment thread
- only `Helpful` and `Not Helpful` are counted in the current implementation
- feedback is not inferred from code changes, reactions, or comments outside the thread
- feedback rate matters as much as helpful rate
- low participation can make the metric unstable
- track positive and negative responses separately
- keep the feedback model simple and unambiguous

**Recommended feedback states**

Each AI comment should support exactly one explicit feedback state from the
viewer:

- `unrated`
- `helpful`
- `not_helpful`

Only comments in `helpful` or `not_helpful` should count as `rated_ai_comments`.

### 5. Applied or Fixed Findings Rate

**Provider support**

| Provider | Supported |
| --- | --- |
| GitHub | Yes |
| GitLab | Yes |
| Bitbucket Cloud | Yes |
| Bitbucket Data Center | Yes |
| Azure DevOps | No (inline review comments are not posted in the current release) |

**Definition**

The percentage of actionable AI findings that are fixed before merge.

**Formula**

```text
Applied or Fixed Findings Rate = fixed_ai_findings / actionable_ai_findings
```

**Primary insight**

This metric connects AI review output to observable code change.

**Why product teams use it**

It is a stronger signal than simple comment counts because it measures whether
the review changed the resulting code.

**Important caveats**

- not every valid finding should be fixed immediately
- distinguish between dismissed, deferred, and fixed
- decide whether one finding can map to multiple commits or code updates

### 6. AI Review Coverage

**Definition**

The percentage of eligible pull requests that receive AI review.

**Formula**

```text
AI Review Coverage = ai_reviewed_prs / total_eligible_prs
```

**Primary insight**

This metric shows whether AI review is part of the normal workflow or only used
in isolated cases.

**Why product teams use it**

Impact claims are weak if only a small or unusual subset of pull requests
receives AI review.

**Important caveats**

- eligibility rules must be stable and explicit
- exclude intentionally unsupported PRs if needed

## Recommended dimensions

Every dashboard or report using the core metrics should support segmentation by
at least these dimensions:

- team
- repository
- Git provider
- PR size bucket
- time window

Recommended PR size buckets:

- small
- medium
- large

The exact thresholds can be defined later, but they should remain stable over
time so trends stay comparable.

## Supporting data model requirements

To measure the six metrics reliably, the system should be able to capture the
following data:

### Pull request lifecycle

- PR identifier per provider
- `pr_opened_at`
- `review_ready_at`
- `merged_at`
- whether AI review ran for the PR

### Human review events

- first human review timestamp
- reviewer identity type so bot activity can be excluded
- event type such as comment, approval, requested changes, or review submission

### AI comment feedback

- AI comment identifier
- comment-to-finding linkage where applicable
- explicit feedback state such as `unrated`, `helpful`, `not_helpful`
- feedback timestamp
- feedback actor

### Finding resolution state

- finding identifier
- finding status such as `open`, `fixed`, `dismissed`, `deferred`
- timestamp of resolution
- optional linkage to the commit or revision where the fix appeared

## Feedback collection (current implementation)

Review analytics currently captures developer feedback only through **direct
replies on AI comment threads** in the Git provider UI.

Supported keywords (exact match after case normalization and trailing punctuation
removal):

- `Helpful`
- `Not Helpful`

The system does **not** infer helpfulness from:

- code changes without a qualifying reply
- emoji reactions or other provider-native reactions
- top-level PR comments that are not threaded replies to an AI comment

GitLab summary comments may not always expose a reply thread in the same way as
inline discussion comments. Prefer replying on the inline AI comment thread when
possible.

## Reporting guidance

When reporting these metrics to users or internal stakeholders:

- use medians for time-based metrics by default
- show trend over time, not only a single snapshot
- show segmented views before drawing conclusions
- pair trust metrics with adoption metrics
- pair outcome metrics with sample size

Examples:

- a lower PR Time to Merge with very low coverage may not generalize
- a high Helpful Rate with very low rating coverage may be misleading
- a lower Time to First Human Reply without better merge outcomes may indicate
  faster engagement but not faster completion

## Out of scope

This document does not define:

- infrastructure or runtime health metrics
- queue and execution latency metrics
- cost metrics such as token spend or compute spend
- model quality benchmarks outside real workflow behavior

Those may be documented separately if the product later needs an operational or
financial analytics view.
