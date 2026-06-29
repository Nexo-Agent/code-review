"""Unit tests for K8sRuntimeProvider submission."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coreview_shared.runtime.k8s.provider import K8sRuntimeProvider
from coreview_shared.schemas.execution_contracts import (
    CallbackConfig,
    CredentialRefs,
    ExecutionConfig,
    ReviewContext,
    ReviewExecutionRequest,
    RuntimeMetadata,
    SecretRef,
)


def _sample_request() -> ReviewExecutionRequest:
    return ReviewExecutionRequest(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        review=ReviewContext(
            repo_full_name="acme/service-a",
            pr_number=42,
            head_sha="abc123",
            git_provider="github",
        ),
        callback=CallbackConfig(
            url="http://cogito-review-api/api/v1/agent/review-events",
            secret_ref=SecretRef(name="review-callback", key="secret"),
        ),
        config=ExecutionConfig(
            workspace_root="/workspaces",
            opencode_agent="code-reviewer",
            llm_provider_id="openai-compat",
            llm_base_url="https://api.example.com/v1",
            llm_model="gpt-4o",
            opencode_model="openai-compat/gpt-4o",
        ),
        credentials=CredentialRefs(
            git_credential_ref=SecretRef(name="review-x-git", key="credentials"),
            llm_credential_ref=SecretRef(name="review-x-llm", key="credentials"),
        ),
        runtime_metadata=RuntimeMetadata(namespace="cogito-review"),
        resolved_secret_env={
            "COGITO_REVIEW_GITHUB_TOKEN": "ghp_test",
            "COGITO_REVIEW_LLM_API_TOKEN": "sk-test",
            "COGITO_REVIEW_CALLBACK_SECRET": "callback-secret",
        },
    )


@pytest.mark.asyncio
async def test_k8s_runtime_provider_submits_crd() -> None:
    provider = K8sRuntimeProvider(
        workspace_root="/workspaces",
        k8s_namespace="cogito-review",
        agent_image="ghcr.io/cogitoforge-ai/cogito-review-agent:latest",
    )

    with patch.object(provider, "_submit_sync") as submit_sync:
        result = await provider.submit_execution(_sample_request())

    submit_sync.assert_called_once()
    assert result.accepted is True
    assert result.backend_kind == "kubernetes"
    assert result.waits_for_completion is False
    assert result.external_ref == (
        "cogito-review/review-550e8400-e29b-41d4-a716-446655440000"
    )


@pytest.mark.asyncio
async def test_k8s_runtime_provider_create_custom_object() -> None:
    provider = K8sRuntimeProvider(
        workspace_root="/workspaces",
        k8s_namespace="cogito-review",
        agent_image="ghcr.io/cogitoforge-ai/cogito-review-agent:latest",
        kubeconfig_path="/tmp/fake-kubeconfig",
    )
    request = _sample_request()

    mock_api = MagicMock()
    mock_core = MagicMock()

    with (
        patch("kubernetes.config.load_kube_config"),
        patch("kubernetes.client.CustomObjectsApi", return_value=mock_api),
        patch("kubernetes.client.CoreV1Api", return_value=mock_core),
    ):
        provider._submit_sync(
            namespace="cogito-review",
            run_name="review-550e8400-e29b-41d4-a716-446655440000",
            request=request,
            run_body={},
        )

    assert mock_core.create_namespaced_secret.call_count == 2
    mock_api.create_namespaced_custom_object.assert_called_once()
    body = mock_api.create_namespaced_custom_object.call_args.kwargs["body"]
    assert body["kind"] == "CogitoReviewRun"
    assert body["spec"]["review"]["reviewId"] == request.review_id
