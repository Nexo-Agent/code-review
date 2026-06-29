# Git Provider

## Purpose

Git providers abstract all source-control-platform-specific behavior required by the system.

The rest of the application should not need to know whether a review came from GitHub, GitLab, Azure DevOps, Bitbucket Cloud, or Bitbucket Data Center.

## Current provider interface responsibilities

Each Git provider implementation is responsible for:

- validating webhook signatures
- parsing webhook payloads into a normalized event
- building PR or MR URLs
- building blob URLs for findings
- fetching PR or MR metadata
- preparing the review workspace
- publishing summary comments
- publishing inline comments
- cleaning up the review workspace

Most provider implementations live in `shared/coreview_shared/providers/git/`.

## Supported providers

Current supported provider keys:

- `github`
- `gitlab`
- `azure-devops`
- `bitbucket`
- `bitbucket-dc`

Provider selection happens through `repo_integrations.git_provider`.

## Provider assembly

Provider construction is centralized in:

- `backend/app/providers/factory.py`
- `agent/app/providers/factory.py`

The system builds a provider bundle from the resolved review runtime configuration.

## Shared design pattern

Despite provider-specific APIs, the current implementations follow a common pattern:

1. fetch provider metadata through the remote API
2. create or reuse a local git workspace through `GitWorkspace`
3. generate the diff locally from git data
4. run review logic against the normalized prepared review
5. publish comments back through the provider API

This pattern keeps review execution consistent across providers.

Workspace preparation and cleanup happen inside the agent runtime. Backend
runtime providers only launch the agent; they do not expose local Git execution
or prepare workspaces on behalf of Git providers.

## Workspace abstraction

The local git workflow is shared through a composed workspace package:

- `shared/coreview_shared/workspace/git_workspace.py`
- `shared/coreview_shared/workspace/git_mirror.py`
- `shared/coreview_shared/workspace/git_worktree.py`
- `shared/coreview_shared/workspace/lock.py`
- `shared/coreview_shared/workspace/diff_builder.py`

`GitWorkspace` is the high-level orchestration entry point used by Git providers.

It composes smaller infrastructure-oriented collaborators:

- `LocalGitExecutor`: runs Git commands locally inside the agent runtime
- `MirrorOperator`: manages bare mirror creation, fetch, and mirror recovery
- `WorktreeOperator`: manages per-review worktree creation, stale worktree pruning, and cleanup
- `WorkspaceLock`: serializes mirror and worktree mutations per repository
- `DiffBuilder`: generates unified diffs from the prepared local worktree

`GitWorkspace` coordinates:

- bare mirror reuse
- fetch and checkout
- per-review worktree creation
- diff generation
- cleanup

Those responsibilities are implemented through dedicated composed classes
rather than a single adapter-centric module or a cross-runtime command runner
abstraction.

## Webhook normalization

Provider-specific webhook payloads are normalized into a shared `WebhookEvent` shape.

Normalized fields include:

- event type
- action
- repository full name
- PR or MR number
- head SHA
- delivery id
- title
- PR or MR URL

This allows webhook routes to reuse a common review-enqueue flow after provider validation.

## Provider-specific notes

### GitHub

- webhook signature: HMAC SHA-256 (`X-Hub-Signature-256`)
- handled actions: `opened`, `synchronize`, `reopened`
- supports inline review comments and issue-style summary comments

### GitLab

- supports both token-style and signed webhook verification
- handles MR open, reopen, and update cases that represent code changes
- skips draft or work-in-progress merge requests

### Azure DevOps

- uses PAT for API access
- webhook authentication is modeled as a Basic auth pair
- review execution works, but CI integration falls back to no-op in this codebase

### Bitbucket Cloud

- verifies HMAC signatures
- supports PR create and update events
- publishes inline and summary comments through Bitbucket APIs

### Bitbucket Data Center

- uses base URL plus bearer token for API access
- webhook authentication is modeled as a Basic auth pair
- supports PR open, reopened, and source-ref update events

## How providers are used

### During webhook ingestion

The backend:

1. resolves the repository integration
2. builds the provider bundle
3. validates the webhook signature
4. parses the webhook

### During review execution

The agent:

1. fetches PR or MR metadata
2. prepares the local review workspace
3. publishes review output back to the provider

### During review display

The backend may rebuild the provider when returning review detail so it can generate:

- canonical PR URLs
- blob URLs for findings

## Adding a new Git provider

To add another provider, the current architecture expects work in these areas:

1. implement a provider class under `shared/coreview_shared/providers/git/`
2. support webhook verification and parsing
3. support metadata fetch and comment publishing
4. wire clone URL and workspace behavior
5. register the provider key in the factory
6. extend repository integration schema and storage if provider-specific credentials are needed
7. add tests for webhook parsing, signature validation, and review comment behavior

## Current architectural trade-off

The code favors a provider abstraction with a shared local git workflow rather than fully independent provider implementations.

Benefits:

- consistent diff generation
- less duplicated review preparation logic
- easier agent behavior across providers

Trade-off:

- providers still need careful API-specific handling for metadata and comment publishing
