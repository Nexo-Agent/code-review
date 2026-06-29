"""Tests for execution contract schemas and models."""

import json
from pathlib import Path

import jsonschema

from coreview_shared.runtime.execution.crd_serialize import (
    cogito_review_run_spec_to_crd,
)
from coreview_shared.schemas.execution_contracts import (
    CallbackConfig,
    CallbackSpec_K8s,
    CogitoReviewRunExecution,
    CogitoReviewRunExecutionSpec,
    CogitoReviewRunReview,
    CogitoReviewRunSpec,
    CredentialRefs,
    ExecutionConfig,
    KubernetesExecutionSpec,
    ResourceRef,
    ReviewContext,
    ReviewExecutionRequest,
    RuntimeMetadata,
    SecretRef,
    WorkspaceSpec_K8s,
)
from coreview_shared.schemas.validation import (
    KUBERNETES_EXECUTION_SPEC_SCHEMA,
    REVIEW_EXECUTION_REQUEST_SCHEMA,
    validate_against_schema,
)


def _sample_secret_ref() -> SecretRef:
    return SecretRef(name="review-creds", key="token", namespace="cogito-review")


def _sample_review_execution_request() -> ReviewExecutionRequest:
    secret = _sample_secret_ref()
    return ReviewExecutionRequest(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        review=ReviewContext(
            repo_full_name="acme/service-a",
            pr_number=42,
            head_sha="abcdef123456",
            git_provider="github",
        ),
        callback=CallbackConfig(
            url="http://cogito-review-api/api/v1/agent/review-events",
            secret_ref=SecretRef(name="review-callback", key="secret"),
            metadata={"delivery_id": "d1"},
        ),
        config=ExecutionConfig(
            workspace_root="/workspaces",
            opencode_agent="code-reviewer",
            opencode_log_level="INFO",
            review_timeout_seconds=600,
            llm_provider_id="openai-compat",
            llm_base_url="https://api.example.com/v1",
            llm_model="gpt-4o",
            opencode_model="openai-compat/gpt-4o",
        ),
        credentials=CredentialRefs(
            git_credential_ref=secret,
            llm_credential_ref=SecretRef(name="llm-creds", key="token"),
        ),
        runtime_metadata=RuntimeMetadata(namespace="cogito-review"),
    )


def test_review_execution_request_validates_against_schema() -> None:
    request = _sample_review_execution_request()
    validate_against_schema(request, REVIEW_EXECUTION_REQUEST_SCHEMA)


def test_kubernetes_execution_spec_validates_against_schema() -> None:
    secret = _sample_secret_ref()
    spec = KubernetesExecutionSpec(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        namespace="cogito-review",
        agent_image="ghcr.io/cogitoforge-ai/cogito-review-agent:0.1.0",
        callback=CallbackSpec_K8s(
            url="http://cogito-review-api/api/v1/agent/review-events",
            secret_ref=SecretRef(name="review-callback", key="secret"),
        ),
        credentials=CredentialRefs(
            git_credential_ref=secret,
            llm_credential_ref=SecretRef(name="llm-creds", key="token"),
        ),
        environment={"COGITO_REVIEW_GIT_PROVIDER": "github"},
        review={
            "repo_full_name": "acme/service-a",
            "pr_number": 42,
            "head_sha": "abcdef123456",
        },
    )
    validate_against_schema(spec, KUBERNETES_EXECUTION_SPEC_SCHEMA)


def test_cogito_review_run_spec_validates_against_schema() -> None:
    secret = _sample_secret_ref()
    run_spec = CogitoReviewRunSpec(
        installation_ref=ResourceRef(name="main", namespace="cogito-review"),
        runtime_policy_ref=ResourceRef(name="default"),
        review=CogitoReviewRunReview(
            review_id="550e8400-e29b-41d4-a716-446655440000",
            repo_full_name="acme/service-a",
            pr_number=42,
            head_sha="abcdef123456",
        ),
        execution=CogitoReviewRunExecution(
            spec=CogitoReviewRunExecutionSpec(
                agent_image="ghcr.io/cogitoforge-ai/cogito-review-agent:0.1.0",
                callback=CallbackSpec_K8s(
                    url="http://cogito-review-api/api/v1/agent/review-events",
                    secret_ref=SecretRef(name="review-callback", key="secret"),
                ),
                workspace=WorkspaceSpec_K8s(),
                credentials=CredentialRefs(
                    git_credential_ref=secret,
                    llm_credential_ref=SecretRef(name="llm-creds", key="token"),
                ),
                environment={"COGITO_REVIEW_GIT_PROVIDER": "github"},
            ),
        ),
        config={"providerRef": "default"},
    )
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "coreview_shared/schemas/cogito-review-run-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=cogito_review_run_spec_to_crd(run_spec), schema=schema)
