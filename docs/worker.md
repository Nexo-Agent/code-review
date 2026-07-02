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
- building the review execution request
- delegating execution submission to the selected runtime provider

It does not perform the review itself.

## Current flow

1. a webhook or retry action enqueues `review.run`
2. Celery worker receives the task
3. worker loads the review row
4. worker resolves repository integration and LLM provider
5. worker constructs a generic execution request for the agent
6. worker invokes the selected runtime provider
7. the runtime provider either launches the agent directly or submits execution intent to Kubernetes
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

The worker does not hard-code container orchestration logic directly in task code.

Instead it uses the runtime provider abstraction:

- `DockerRuntimeProvider` translates the execution request into a Docker job spec and launches the one-shot agent container through the Docker Engine API
- `K8sRuntimeProvider` translates the execution request into Kubernetes execution data, creates or updates the supporting Secrets, and publishes a `CogitoReviewRun` custom resource to the Kubernetes API

In Kubernetes mode, the worker does not create the review `Job` itself.
The Cogito Review Operator watches `CogitoReviewRun` resources and reconciles the actual agent `Job`.

This keeps orchestration separate from business logic while preserving one shared worker flow.

## Required infrastructure

For Docker-based execution, the worker needs:

- Redis connectivity
- PostgreSQL connectivity
- a writable shared workspace mount
- access to the Docker socket
- the configured agent image available to the Docker host

For Kubernetes-based execution, the worker needs:

- Redis connectivity
- PostgreSQL connectivity
- access to the Kubernetes API, either in cluster or through kubeconfig
- permission to create or patch review execution Secrets
- permission to create or patch `CogitoReviewRun` custom resources

## Worker versus API responsibilities

### API

- receives webhooks
- creates review rows
- exposes user-facing endpoints
- receives agent callbacks

### Worker

- turns a review row into a backend-neutral execution request
- submits isolated execution to the configured runtime backend

### Agent

- performs repository analysis
- talks to Git and CI providers
- posts comments and findings

## Current deployment shape

In Docker Compose, the worker is a separate service using the same main image as the API with a different command:

`cogito-review job worker --concurrency 1`

This keeps operational packaging simple while preserving process separation.

In Kubernetes mode, the worker still runs as a separate deployment, but its role changes slightly:

- it submits execution intent to the Kubernetes control plane
- the Operator creates and tracks the actual agent `Job`

## Current limitations

- worker security is sensitive because of Docker socket access
- Kubernetes execution depends on the Operator and CRDs being installed and healthy
- job concurrency and queue partitioning are still relatively simple
