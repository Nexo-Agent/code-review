"""Execution request translation and submission helpers."""

from __future__ import annotations

from coreview_shared.schemas.execution_contracts import (
    CallbackSpec_K8s,
    CogitoReviewRunExecution,
    CogitoReviewRunExecutionSpec,
    CogitoReviewRunReview,
    CogitoReviewRunSpec,
    KubernetesExecutionSpec,
    ResourceRef,
    ReviewExecutionRequest,
    WorkspaceSpec_K8s,
)


def build_kubernetes_execution_spec(
    request: ReviewExecutionRequest,
    *,
    agent_image: str,
    namespace: str,
) -> KubernetesExecutionSpec:
    non_secret_env = _non_secret_environment(request)
    return KubernetesExecutionSpec(
        review_id=request.review_id,
        namespace=namespace,
        installation_ref=request.runtime_metadata.installation_ref,
        runtime_policy_ref=request.runtime_metadata.runtime_policy_ref,
        scaling_policy_ref=request.runtime_metadata.scaling_policy_ref,
        agent_image=agent_image,
        callback=CallbackSpec_K8s(
            url=request.callback.url,
            secret_ref=request.callback.secret_ref,
        ),
        workspace=WorkspaceSpec_K8s(root_path=request.config.workspace_root),
        credentials=request.credentials,
        environment=non_secret_env,
        review={
            "repo_full_name": request.review.repo_full_name,
            "pr_number": request.review.pr_number,
            "head_sha": request.review.head_sha,
        },
        config={
            "llm_ref": request.config.llm_provider_id,
            "provider_ref": request.review.git_provider,
        },
    )


def build_cogito_review_run_spec(
    k8s_spec: KubernetesExecutionSpec,
) -> CogitoReviewRunSpec:
    installation_ref = None
    if k8s_spec.installation_ref:
        installation_ref = ResourceRef(
            name=k8s_spec.installation_ref,
            namespace=k8s_spec.namespace,
        )
    runtime_policy_ref = None
    if k8s_spec.runtime_policy_ref:
        runtime_policy_ref = ResourceRef(
            name=k8s_spec.runtime_policy_ref,
            namespace=k8s_spec.namespace,
        )
    scaling_policy_ref = None
    if k8s_spec.scaling_policy_ref:
        scaling_policy_ref = ResourceRef(
            name=k8s_spec.scaling_policy_ref,
            namespace=k8s_spec.namespace,
        )

    return CogitoReviewRunSpec(
        installation_ref=installation_ref,
        runtime_policy_ref=runtime_policy_ref,
        scaling_policy_ref=scaling_policy_ref,
        review=CogitoReviewRunReview(
            review_id=k8s_spec.review_id,
            repo_full_name=str(k8s_spec.review.get("repo_full_name", "")),
            pr_number=int(k8s_spec.review.get("pr_number", 0)),
            head_sha=str(k8s_spec.review.get("head_sha", "")),
        ),
        execution=CogitoReviewRunExecution(
            spec=CogitoReviewRunExecutionSpec(
                agent_image=k8s_spec.agent_image,
                callback=k8s_spec.callback,
                workspace=k8s_spec.workspace,
                credentials=k8s_spec.credentials,
                environment=k8s_spec.environment,
            ),
        ),
        config=k8s_spec.config,
    )


def _non_secret_environment(request: ReviewExecutionRequest) -> dict[str, str]:
    cfg = request.config
    review = request.review
    env: dict[str, str] = {
        "COGITO_REVIEW_REPO_FULL_NAME": review.repo_full_name,
        "COGITO_REVIEW_PR_NUMBER": str(review.pr_number),
        "COGITO_REVIEW_HEAD_SHA": review.head_sha,
        "COGITO_REVIEW_GIT_PROVIDER": review.git_provider,
        "COGITO_REVIEW_LLM_PROVIDER_ID": cfg.llm_provider_id,
        "COGITO_REVIEW_LLM_BASE_URL": cfg.llm_base_url,
        "COGITO_REVIEW_LLM_MODEL": cfg.llm_model,
        "COGITO_REVIEW_OPENCODE_MODEL": cfg.opencode_model,
        "COGITO_REVIEW_OPENCODE_AGENT": cfg.opencode_agent,
        "COGITO_REVIEW_REVIEW_TIMEOUT_SECONDS": str(cfg.review_timeout_seconds),
        "COGITO_REVIEW_OPENCODE_LOG_LEVEL": cfg.opencode_log_level,
        "COGITO_REVIEW_WORKSPACE_ROOT": cfg.workspace_root,
        "COGITO_REVIEW_REVIEW_ID": request.review_id,
        "COGITO_REVIEW_CALLBACK_URL": request.callback.url,
        "COGITO_REVIEW_CALLBACK_METADATA": _metadata_json(request),
        "PYTHONUNBUFFERED": "1",
    }
    if cfg.system_prompt.strip():
        env["COGITO_REVIEW_SYSTEM_PROMPT"] = cfg.system_prompt
    return env


def _metadata_json(request: ReviewExecutionRequest) -> str:
    import json

    return json.dumps(request.callback.metadata)
