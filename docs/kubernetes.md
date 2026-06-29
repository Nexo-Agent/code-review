# Kubernetes Integration

## Purpose

This document outlines the target Kubernetes-native architecture for Cogito Review.

It is a technical design draft, not an implementation-complete deployment guide.

The goal is to support a Kubernetes installation mode that:

- keeps the current core application logic
- introduces Kubernetes-native installation and runtime control through an Operator
- allows the product to continue supporting a separate Docker runtime installation mode

## Installation modes

Cogito Review supports two installation modes.

### Docker mode

Docker mode keeps the current container-based deployment model.

- deployment path: Docker Compose or equivalent container tooling
- review runtime: Docker
- orchestration model: worker launches one-shot agent containers
- Kubernetes CRDs and Operator: not required

This mode is intended for local development, simple self-hosting, and environments that do not want a Kubernetes-native control plane.

### Kubernetes mode

Kubernetes mode is an Operator-managed installation model.

- deployment path: Kubernetes manifests installed and reconciled by a Cogito Review Operator
- review runtime: Kubernetes-native execution
- orchestration model: Kubernetes resources such as Jobs, Deployments, Services, Secrets, and ServiceAccounts
- Kubernetes CRDs and Operator: required

This mode is intended for production Kubernetes platforms and GitOps-style environments.

## Core design principle

The core application logic remains shared between installation modes.

This includes:

- webhook ingestion
- review persistence
- repository integration resolution
- LLM provider resolution
- review callback handling
- review execution logic inside the agent image
- provider integrations for Git and CI
- shared runtime contracts and callback schemas

The Kubernetes integration adds a platform-specific control layer on top of the current core.

Kubernetes-specific behavior should live in the Operator and Kubernetes runtime integration, not in duplicated business logic.

## Runtime abstraction direction

The Kubernetes integration changes the meaning of the current runtime abstraction.

Today the runtime path is largely shaped around direct execution.

- Docker mode launches an agent container directly
- workspace preparation and execution dispatch are bundled together

That model does not fit the Operator-managed Kubernetes mode.

In Kubernetes mode:

- the backend or worker prepares a generic execution intent
- the Kubernetes runtime adapter translates that intent into Kubernetes-facing execution data
- the adapter submits that intent to the Kubernetes control plane by creating or updating CRD-backed resources
- the Operator reconciles the actual Kubernetes Jobs and supporting resources

Because of this, the runtime abstraction should evolve toward a two-layer model:

- a generic execution request shared by the core application
- backend-specific execution adapters

The target execution model is:

- `ReviewExecutionRequest`: generic, backend-neutral execution intent
- `DockerExecutionSpec`: Docker-specific execution translation
- `KubernetesExecutionSpec`: Kubernetes-specific execution translation

## Runtime protocol split

The runtime protocol is execution-only.

The backend and worker submit a generic execution request to the selected
backend, and the backend-specific runtime adapter is responsible only for:

- accepting a generic execution request
- translating it into backend-specific execution data
- submitting that execution to the selected backend
- returning a submission result

Repository-local workspace behavior does not belong to the runtime backend.
Mirror preparation, worktree checkout, diff generation, and cleanup all happen
inside the agent runtime after the backend launches the agent.

That agent-local workflow uses concrete local Git execution inside the agent
process. Kubernetes and Docker runtime adapters do not provide a shared command
runner or Git execution hook back into the workspace layer.

This keeps the interface honest for both modes:

- Docker mode translates the request into a `DockerExecutionSpec` and runs the agent directly
- Kubernetes mode translates the request into a `KubernetesExecutionSpec` and publishes a `CogitoReviewRun`

## Submission semantics

The old name `run_review_job()` suggests direct execution ownership.

The new name `submit_execution()` is preferred because it is valid for both installation modes.

In Docker mode:

- submit means execute immediately through the Docker backend

In Kubernetes mode:

- submit means publish execution intent to the Kubernetes control plane
- actual execution happens later through the Operator reconcile loop

The return type should be modeled as a submission result rather than a final execution result.

Suggested fields include:

- backend kind
- accepted status
- submission timestamp
- external reference

Examples of external references:

- Docker container or execution identifier
- Kubernetes `namespace/name` for a `CogitoReviewRun`

## Architectural boundary

### Core application responsibilities

The existing application remains responsible for:

- serving the REST API and frontend
- storing business state in PostgreSQL
- receiving webhooks
- creating review records
- validating callbacks from the review agent
- storing findings and review metadata
- enforcing product RBAC and authentication behavior

### Operator responsibilities

The Operator is responsible for Kubernetes-native installation and lifecycle management.

This includes:

- reconciling the Cogito Review installation in a cluster
- creating and updating platform workloads such as API, worker, migration Job, and supporting Services
- binding Secrets and ConfigMaps to workloads
- managing runtime policy for Kubernetes review execution
- creating and managing Kubernetes Jobs for review agents
- exposing operational status through CRD status and conditions
- cleaning up owned Kubernetes resources through owner references and finalizers
- supporting Kubernetes-native scaling, scheduling, and lifecycle controls
- resolving Kubernetes-native secret material for runtime workloads

### Separation of concerns

The Operator should not re-implement application business rules.

It should not become responsible for:

- repository-level business logic
- findings storage semantics
- review content generation
- provider-specific comment publishing rules
- application-level RBAC decisions

Its role is to orchestrate Kubernetes resources around the existing product.

## High-level Kubernetes topology

In Kubernetes mode, one Cogito Review installation is managed by one root custom resource.

Typical topology:

- one API Deployment
- one worker Deployment
- one migration Job or hook-based migration workflow
- PostgreSQL connectivity, either external or cluster-managed by another system
- Redis connectivity, either external or in-cluster
- one-shot review agent Jobs created on demand
- supporting Services, ServiceAccounts, Secrets, ConfigMaps, and optional Ingress resources

The agent remains a separate image and continues to communicate with the backend through callbacks.

## Operator scope

The Operator is the Kubernetes-native extension for Cogito Review.

Its responsibilities are grouped into six areas.

### 1. Installation

The Operator installs and reconciles the main Cogito Review application components.

This includes:

- API Deployment
- worker Deployment
- migration Job
- Services
- ConfigMaps
- Secret projections
- optional Ingress
- optional PodDisruptionBudgets
- optional HorizontalPodAutoscalers

### 2. Topology

The Operator defines and maintains the workload topology of the installation.

This includes:

- which components exist
- how they connect
- what images they use
- which services are exposed
- which runtime profiles are available to the installation

### 3. Runtime policy

The Operator controls how review execution runs in Kubernetes mode.

This includes:

- agent image selection
- timeout and retry behavior
- cleanup behavior
- resource requests and limits
- service account and image pull secrets
- workspace preparation strategy
- scheduling and affinity hints
- network and egress policy references
- CRD-backed execution intent handling

### 4. Scaling

The Operator controls scaling for long-running workloads and burst execution.

This includes:

- API replica count
- worker replica count
- worker concurrency-related configuration
- autoscaling integration for API and worker
- execution concurrency caps for review agent Jobs

### 5. Secret references

The Operator binds Kubernetes-native secret references into the installation.

This includes:

- database credentials
- Redis credentials
- callback secret
- session and encryption secrets
- image pull secrets
- installation-level provider credential references
- review execution credential references

The Operator should resolve Kubernetes Secrets and project them into the actual runtime workloads.

The backend or worker should not provision Kubernetes Jobs with embedded raw secret values in the Kubernetes mode path.

### 6. Lifecycle

The Operator manages lifecycle concerns.

This includes:

- installation creation
- drift reconciliation
- version upgrades
- secret rotation propagation
- stale Job cleanup
- uninstall cleanup
- finalizer-based teardown
- status condition reporting

## Proposed CRDs

The Kubernetes mode should start with a small set of CRDs focused on installation and execution control.

The initial proposal includes:

- `CogitoReviewInstallation`
- `CogitoReviewRuntimePolicy`
- `CogitoReviewScalingPolicy`
- `CogitoReviewRun`

Additional CRDs can be added later if operational needs justify them.

## `CogitoReviewInstallation`

### Purpose

`CogitoReviewInstallation` is the root resource for one Operator-managed Cogito Review instance.

It defines the desired application installation in Kubernetes mode.

### Scope

This resource should own:

- API Deployment
- worker Deployment
- migration Job
- Services
- ConfigMaps
- ServiceAccounts
- optional Ingress
- optional PodDisruptionBudgets
- optional HorizontalPodAutoscalers

### Suggested `spec` structure

The exact schema can evolve, but the shape should be close to:

```yaml
apiVersion: platform.cogito.review/v1alpha1
kind: CogitoReviewInstallation
metadata:
  name: main
spec:
  version: "0.1.0"
  images:
    app: ghcr.io/cogitoforge-ai/cogito-review:0.1.0
    agent: ghcr.io/cogitoforge-ai/cogito-review-agent:0.1.0
  ingress:
    enabled: true
    className: nginx
    host: review.example.com
    tlsSecretRef:
      name: review-tls
  database:
    mode: external
    urlSecretRef:
      name: review-db
      key: DATABASE_URL
  redis:
    mode: external
    urlSecretRef:
      name: review-redis
      key: REDIS_URL
  frontend:
    publicUrl: https://review.example.com
  auth:
    enabled: true
  secrets:
    callbackSecretRef:
      name: review-callback
      key: secret
    sessionSecretRef:
      name: review-session
      key: secret
    encryptionKeySecretRef:
      name: review-encryption
      key: key
  runtimePolicyRef:
    name: default
  scalingPolicyRef:
    name: default
  components:
    api:
      replicas: 2
    worker:
      replicas: 1
```

### Suggested `status` structure

`status` should provide operator-facing operational state.

Suggested fields:

- `phase`
- `observedGeneration`
- `observedVersion`
- `conditions`
- `endpoints`
- `availableComponents`
- `runtimeStatus`

Example condition types:

- `Ready`
- `Progressing`
- `Degraded`
- `DatabaseReady`
- `RedisReady`
- `ApiReady`
- `WorkerReady`
- `RuntimePolicyResolved`
- `SecretsResolved`

## `CogitoReviewRuntimePolicy`

### Purpose

`CogitoReviewRuntimePolicy` defines how review execution should run in Kubernetes mode.

It is intentionally focused on execution behavior, not full installation topology.

### Why separate it

Separating runtime policy from installation allows:

- reuse across installations
- clearer GitOps review of execution settings
- future policy versioning without overloading the root installation resource

### Suggested `spec` structure

```yaml
apiVersion: platform.cogito.review/v1alpha1
kind: CogitoReviewRuntimePolicy
metadata:
  name: default
spec:
  executor:
    type: kubernetes-job
    namespace: cogito-review
    serviceAccountName: cogito-review-agent
    imagePullSecrets:
      - name: ghcr-creds
  job:
    ttlSecondsAfterFinished: 3600
    backoffLimit: 0
    activeDeadlineSeconds: 900
    cleanup:
      deleteFailedJobsAfterSeconds: 86400
      deleteSucceededJobsAfterSeconds: 3600
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "1"
      memory: "2Gi"
  scheduling:
    nodeSelector: {}
    tolerations: []
    affinity: {}
  network:
    policyProfile: default
  workspace:
    strategy: ephemeral-clone
    rootPath: /workspaces
  execution:
    timeoutSeconds: 600
    callbackMode: internal-service
    submissionMode: operator-crd
```

### Suggested `status` structure

Suggested fields:

- `conditions`
- `effectiveExecutor`
- `validationErrors`
- `resolvedServiceAccount`
- `resolvedNamespace`

Example condition types:

- `Ready`
- `Valid`
- `ExecutorAvailable`
- `ServiceAccountReady`

## `CogitoReviewScalingPolicy`

### Purpose

`CogitoReviewScalingPolicy` defines scaling behavior for long-running application components and review execution throughput.

### Suggested `spec` structure

```yaml
apiVersion: platform.cogito.review/v1alpha1
kind: CogitoReviewScalingPolicy
metadata:
  name: default
spec:
  api:
    replicas: 2
    autoscaling:
      enabled: true
      minReplicas: 2
      maxReplicas: 5
      targetCPUUtilizationPercentage: 70
  worker:
    replicas: 1
    autoscaling:
      enabled: false
    concurrency:
      celeryWorkerConcurrency: 1
      maxQueuedReviewsPerWorker: 10
  execution:
    maxConcurrentReviewJobs: 10
```

### Suggested `status` structure

Suggested fields:

- `conditions`
- `effectiveReplicas`
- `effectiveConcurrency`
- `capacityWarnings`

## `CogitoReviewRun`

### Purpose

`CogitoReviewRun` is the execution-intent resource for one review run in Kubernetes mode.

This resource is optional in the overall product direction, but it is the cleanest way for the Operator to own Kubernetes-native execution lifecycle without re-implementing product business state.

### Recommended role

The backend remains the source of truth for review records.

The role of `CogitoReviewRun` is:

- to represent execution intent in Kubernetes
- to allow the Operator to create and observe the agent Job
- to expose operational status in Kubernetes-native form

The backend may create this resource when a review should run.

### Suggested `spec` structure

```yaml
apiVersion: platform.cogito.review/v1alpha1
kind: CogitoReviewRun
metadata:
  name: review-123
spec:
  installationRef:
    name: main
  runtimePolicyRef:
    name: default
  scalingPolicyRef:
    name: default
  review:
    reviewId: "123e4567-e89b-12d3-a456-426614174000"
    repoFullName: acme/service-a
    prNumber: 42
    headSha: abcdef123456
  execution:
    kind: kubernetes
    spec:
      agentImage: ghcr.io/cogitoforge-ai/cogito-review-agent:0.1.0
      callback:
        mode: internal-service
        url: http://cogito-review-api/api/v1/agent/review-events
        secretRef:
          name: review-callback
          key: secret
      workspace:
        strategy: ephemeral-clone
        rootPath: /workspaces
      credentials:
        gitCredentialRef:
          name: github-review-token
          key: token
        llmCredentialRef:
          name: llm-provider-token
          key: token
  config:
    providerRef: default
    llmRef: default
    systemPromptRef: repo-default
```

### Suggested `status` structure

Suggested fields:

- `phase`
- `conditions`
- `selectedExecutor`
- `jobRef`
- `podRefs`
- `startedAt`
- `completedAt`
- `exitCode`
- `failureReason`
- `callbackObserved`

Example phases:

- `Pending`
- `Scheduled`
- `Running`
- `Succeeded`
- `Failed`
- `TimedOut`
- `CleanedUp`

### Why this resource fits the hybrid model

`CogitoReviewRun` captures infrastructure execution state, not the full product review domain.

The review findings, persisted review status, and user-facing behavior still remain in the existing backend and database model.

## CRD relationships

The intended ownership model is:

- `CogitoReviewInstallation` is the root object
- `CogitoReviewRuntimePolicy` is referenced by the installation and by review runs
- `CogitoReviewScalingPolicy` is referenced by the installation and by review runs when needed
- `CogitoReviewRun` references the installation and runtime policy

Expected Kubernetes ownership patterns:

- workload resources created for the installation are owned by `CogitoReviewInstallation`
- agent Jobs created for one review run are owned by `CogitoReviewRun`
- finalizers are used when external cleanup is needed before resource deletion

## Kubernetes runtime integration model

## Runtime contract

The current execution model should evolve into a generic execution contract plus backend-specific adapters.

The target structure is:

- `ReviewExecutionRequest`
- `DockerExecutionSpec`
- `KubernetesExecutionSpec`

`ReviewExecutionRequest` is the canonical execution intent produced by the core application.

It should contain:

- review identity
- repository execution context
- callback configuration
- execution policy snapshot
- runtime metadata
- non-secret configuration needed for execution
- references to credentials and other sensitive material

`DockerExecutionSpec` is derived from `ReviewExecutionRequest` for Docker mode.

`KubernetesExecutionSpec` is derived from `ReviewExecutionRequest` for Kubernetes mode.

The Kubernetes adapter should then map `KubernetesExecutionSpec` into `CogitoReviewRun` resources and other CRD-backed objects as needed.

The backend still owns:

- review preparation
- business configuration resolution
- review record persistence
- callback processing

The Operator owns:

- Kubernetes-native secret resolution
- review agent Job creation
- Kubernetes resource lifecycle
- runtime status reconciliation

## Proposed flow

A target Kubernetes review flow is:

1. a Git provider sends a webhook
2. the backend validates the request and creates a review row
3. the worker prepares a `ReviewExecutionRequest`
4. the Kubernetes runtime adapter derives a `KubernetesExecutionSpec`
5. the Kubernetes runtime adapter submits a `CogitoReviewRun` resource
6. the Operator resolves referenced Secrets and installation-level bindings
7. the Operator reconciles the resource
8. the Operator creates a one-shot Kubernetes Job for the review agent
9. the agent prepares the repository workspace inside the Job Pod
10. the agent runs the review and posts comments to the Git provider
11. the agent sends callbacks to the backend
12. the backend persists findings and final review state
13. the Operator observes Job completion and updates `CogitoReviewRun.status`

This keeps business state in the application while exposing execution state in Kubernetes.

## Workspace strategy

The initial Kubernetes runtime should prefer an ephemeral workspace strategy.

Recommended initial behavior:

- one agent Job handles one review run
- the Job Pod clones and prepares the repository inside its own filesystem
- the workspace is deleted with the Pod

This avoids forcing the Docker named-volume model into Kubernetes.

Future optimization options can include:

- PVC-based cache
- remote mirror cache
- init container clone strategies

## Secret and configuration flow

Kubernetes mode should prefer Kubernetes-native secret references for installation-level configuration.

Recommended pattern:

- infrastructure secrets are provided as Kubernetes Secrets
- execution requests carry configuration plus secret references, not raw secret values
- CRDs reference those Secrets or logical bindings that the Operator can resolve
- the Operator projects the resolved secret material into Deployments and Jobs

Examples:

- `DATABASE_URL`
- Redis URL or credentials
- callback signing secret
- session secret
- encryption key
- image pull secrets
- provider access credentials
- LLM access credentials

### Worker-prepared data

The worker should prepare:

- review identity
- repository execution context
- selected runtime mode
- execution policy snapshot
- callback target details
- non-secret execution configuration
- references to required credentials

### Operator-resolved data

The Operator should resolve:

- Kubernetes Secret values
- installation-level credential bindings
- runtime environment materialization for Jobs
- any cluster-local configuration needed to mount or inject secrets into workloads

This keeps security-sensitive material in Kubernetes-native secret storage rather than embedding it directly into CRD specs or backend-generated environment payloads.

Application-managed provider credentials can remain in PostgreSQL in the initial hybrid design.

Longer term, the system may support optional Kubernetes secret-backed provider configuration without making it mandatory.

## Schema authority and Python/Go independence

The Kubernetes integration creates a cross-language contract between:

- the Python backend and worker
- the Go Operator

Those codebases should remain implementation-independent.

The canonical source of truth for integration contracts should therefore be schema artifacts, not Python classes and not Go structs.

Recommended direction:

- define versioned schema artifacts for execution contracts
- validate Python-side models against those artifacts
- implement Go-side CRD and controller models against the same contracts
- add compatibility tests so changes are reviewed as contract changes, not just local refactors

Suggested contract artifacts include:

- `review-execution-request-v1.schema.json`
- `kubernetes-execution-spec-v1.schema.json`
- `cogito-review-run-v1.schema.json`

These contracts should be treated as internal public APIs between the core application and the Operator.

The contributor guidance should explicitly state that:

- Python and Go implementations are independent
- shared integration contracts are schema-first
- cross-language contract changes require compatibility review
- secrets should not be embedded directly in CRD specs unless explicitly justified

## Scheduling and scaling behavior

The Kubernetes runtime should expose first-class scheduling controls.

Examples:

- node selectors
- tolerations
- affinity
- priority classes
- resource requests and limits
- execution concurrency caps

This is an Operator concern, not business logic inside the core application.

## Lifecycle and cleanup

The Operator should manage the lifecycle of review agent Jobs.

Recommended behavior:

- create one Job per `CogitoReviewRun`
- observe Job and Pod state
- update `status.conditions`
- enforce timeout through Kubernetes Job configuration and runtime policy
- delete stale Jobs according to cleanup policy
- preserve enough status and logs for debugging

## How Kubernetes mode coexists with Docker mode

Kubernetes mode and Docker mode are two supported installation modes of the same product.

### Shared between modes

- backend logic
- agent logic
- shared protocols
- callback schema
- review formatting and provider integrations

### Different between modes

- packaging and deployment model
- runtime execution backend
- infrastructure lifecycle control
- scaling model
- secret delivery model
- operational status surface

### Important design implication

The Kubernetes CRDs should describe the Kubernetes-managed installation mode only.

They should not try to model Docker installation mode as a CRD-backed topology.

Docker mode remains a separate deployment path outside the Operator.

## Suggested implementation boundaries

The current repository should evolve toward the following boundary:

### Core packages

`shared/`, `backend/`, and `agent/` should continue to own:

- review request construction
- provider resolution
- callback protocol
- review execution logic
- business persistence

### Operator package

A future Operator package should own:

- CRDs
- reconciliation loops
- Kubernetes resource generation
- status and condition updates
- cleanup and finalizers
- Kubernetes-native runtime execution orchestration

## Future extensions

Possible future Kubernetes-specific extensions include:

- repository or team-specific runtime classes
- optional Secret-backed provider configuration from Kubernetes
- ServiceMonitor integration
- PrometheusRule integration
- NetworkPolicy templates
- admission validation for CRDs
- multi-namespace installation strategies

These should remain additive platform features, not a rewrite of core product logic.

## Current status

This document describes the target design direction.

At the time of writing:

- Docker mode is the implemented production path
- Kubernetes runtime abstractions exist in the shared codebase
- Kubernetes-native installation, CRDs, and Operator workflows are not yet fully implemented

This document should be treated as the baseline draft for that future work.
