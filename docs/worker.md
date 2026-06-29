# Worker

## Purpose

The worker is the background execution component that takes queued review jobs and launches isolated review runs.

It exists so webhook handling and browser APIs do not need to perform long-running review work inline.

## Technology stack

- Celery for background tasks
- Redis as broker and result backend
- shared backend application code for review preparation

Main files:

- `backend/app/jobs/celery_app.py`
- `backend/app/jobs/review.py`
- `backend/app/services/review_runner.py`

## Responsibilities

The worker is responsible for:

- consuming `review.run` jobs
- loading review configuration from PostgreSQL
- resolving the repository integration and LLM provider
- building the agent environment
- delegating execution to the runtime provider

It does not perform the review itself.

## Current flow

1. a webhook or retry action enqueues `review.run`
2. Celery worker receives the task
3. worker loads the review row
4. worker resolves repository integration and LLM provider
5. worker constructs the environment for the agent
6. worker invokes the runtime provider
7. runtime launches a one-shot agent container
8. agent reports final state back to the API through callbacks

## Queue model

Celery is configured with:

- JSON task serialization
- Redis broker URL from `COGITO_REVIEW_CELERY_BROKER_URL`
- soft and hard time limits derived from review timeout settings

The main task is named:

- `review.run`

## Retry behavior

The Celery task currently retries on failure:

- max retries: `2`
- retry delay: `30` seconds

This retry is about worker-side dispatch failures. The final persisted review outcome still depends on whether the agent reports completion or failure.

## Runtime delegation

The worker does not hard-code Docker commands directly in task code.

Instead it uses the runtime provider abstraction:

- `DockerRuntimeProvider` is implemented
- `K8sRuntimeProvider` exists but review execution is not implemented

This keeps orchestration separate from business logic.

## Required infrastructure

For the current Docker-based execution model, the worker needs:

- Redis connectivity
- PostgreSQL connectivity
- a writable shared workspace mount
- access to the Docker socket
- the configured agent image available to the Docker host

## Worker versus API responsibilities

### API

- receives webhooks
- creates review rows
- exposes user-facing endpoints
- receives agent callbacks

### Worker

- turns a review row into an executable job
- launches isolated execution

### Agent

- performs repository analysis
- talks to Git and CI providers
- posts comments and findings

## Current deployment shape

In Docker Compose, the worker is a separate service using the same main image as the API with a different command:

`cogito-review job worker --concurrency 1`

This keeps operational packaging simple while preserving process separation.

## Current limitations

- review execution runtime is effectively Docker-only today
- worker security is sensitive because of Docker socket access
- job concurrency and queue partitioning are still relatively simple
