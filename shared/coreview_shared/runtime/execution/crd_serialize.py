"""Serialize CogitoReviewRun spec using CRD camelCase field names."""

from __future__ import annotations

from typing import Any

from coreview_shared.schemas.execution_contracts import (
    CallbackSpec_K8s,
    CogitoReviewRunExecutionSpec,
    CogitoReviewRunReview,
    CogitoReviewRunSpec,
    CredentialRefs,
    ResourceRef,
    SecretRef,
    WorkspaceSpec_K8s,
)


def secret_ref_to_crd(ref: SecretRef) -> dict[str, str]:
    out: dict[str, str] = {"name": ref.name, "key": ref.key}
    if ref.namespace:
        out["namespace"] = ref.namespace
    return out


def resource_ref_to_crd(ref: ResourceRef | None) -> dict[str, str] | None:
    if ref is None:
        return None
    out: dict[str, str] = {"name": ref.name}
    if ref.namespace:
        out["namespace"] = ref.namespace
    return out


def credentials_to_crd(creds: CredentialRefs) -> dict[str, Any]:
    return {
        "gitCredentialRef": secret_ref_to_crd(creds.git_credential_ref),
        "llmCredentialRef": secret_ref_to_crd(creds.llm_credential_ref),
    }


def callback_to_crd(callback: CallbackSpec_K8s) -> dict[str, Any]:
    return {
        "mode": callback.mode,
        "url": callback.url,
        "secretRef": secret_ref_to_crd(callback.secret_ref),
    }


def workspace_to_crd(workspace: WorkspaceSpec_K8s) -> dict[str, str]:
    return {"strategy": workspace.strategy, "rootPath": workspace.root_path}


def execution_spec_to_crd(spec: CogitoReviewRunExecutionSpec) -> dict[str, Any]:
    return {
        "agentImage": spec.agent_image,
        "callback": callback_to_crd(spec.callback),
        "workspace": workspace_to_crd(spec.workspace),
        "credentials": credentials_to_crd(spec.credentials),
        "environment": spec.environment,
    }


def review_to_crd(review: CogitoReviewRunReview) -> dict[str, Any]:
    return {
        "reviewId": review.review_id,
        "repoFullName": review.repo_full_name,
        "prNumber": review.pr_number,
        "headSha": review.head_sha,
    }


def cogito_review_run_spec_to_crd(spec: CogitoReviewRunSpec) -> dict[str, Any]:
    out: dict[str, Any] = {
        "review": review_to_crd(spec.review),
        "execution": {
            "kind": spec.execution.kind,
            "spec": execution_spec_to_crd(spec.execution.spec),
        },
    }
    if spec.config:
        out["config"] = spec.config
    if spec.installation_ref is not None:
        out["installationRef"] = resource_ref_to_crd(spec.installation_ref)
    if spec.runtime_policy_ref is not None:
        out["runtimePolicyRef"] = resource_ref_to_crd(spec.runtime_policy_ref)
    if spec.scaling_policy_ref is not None:
        out["scalingPolicyRef"] = resource_ref_to_crd(spec.scaling_policy_ref)
    return out
