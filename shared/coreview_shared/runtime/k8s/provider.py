"""Kubernetes runtime provider that submits agent execution intent."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from coreview_shared.runtime.execution.crd_serialize import (
    cogito_review_run_spec_to_crd,
)
from coreview_shared.runtime.execution.translate import (
    build_cogito_review_run_spec,
    build_kubernetes_execution_spec,
)
from coreview_shared.schemas.execution_contracts import (
    ExecutionSubmissionResult,
    ReviewExecutionRequest,
    SecretRef,
)

logger = logging.getLogger(__name__)

COGITO_REVIEW_RUN_GROUP = "platform.cogito.review"
COGITO_REVIEW_RUN_VERSION = "v1alpha1"
COGITO_REVIEW_RUN_PLURAL = "cogitoreviewruns"


class K8sRuntimeProvider:
    def __init__(
        self,
        *,
        workspace_root: str,
        agent_image: str = "cogito-review-agent:dev",
        database_url: str = "",
        k8s_namespace: str = "cogito-review",
        k8s_agent_config_configmap: str = "opencode-config",
        kubeconfig_path: str = "",
    ) -> None:
        self._workspace_root = workspace_root
        self._agent_image = agent_image
        self._database_url = database_url
        self._k8s_namespace = k8s_namespace
        self._k8s_agent_config_configmap = k8s_agent_config_configmap
        self._kubeconfig_path = kubeconfig_path

    async def submit_execution(
        self, request: ReviewExecutionRequest
    ) -> ExecutionSubmissionResult:
        namespace = request.runtime_metadata.namespace or self._k8s_namespace
        k8s_spec = build_kubernetes_execution_spec(
            request,
            agent_image=self._agent_image,
            namespace=namespace,
        )
        run_spec = build_cogito_review_run_spec(k8s_spec)
        run_name = f"review-{request.review_id}"

        await asyncio.to_thread(
            self._submit_sync,
            namespace=namespace,
            run_name=run_name,
            request=request,
            run_body=run_spec.model_dump(mode="json", exclude_none=True),
        )

        external_ref = f"{namespace}/{run_name}"
        logger.info("Submitted CogitoReviewRun %s", external_ref)
        return ExecutionSubmissionResult(
            backend_kind="kubernetes",
            accepted=True,
            submitted_at=datetime.now(UTC),
            external_ref=external_ref,
            waits_for_completion=False,
        )

    def _submit_sync(
        self,
        *,
        namespace: str,
        run_name: str,
        request: ReviewExecutionRequest,
        run_body: dict[str, Any],
    ) -> None:
        from kubernetes import client, config

        if self._kubeconfig_path:
            config.load_kube_config(config_file=self._kubeconfig_path)
        else:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()

        api = client.CustomObjectsApi()
        core = client.CoreV1Api()

        git_secret_name = f"review-{request.review_id}-git"
        llm_secret_name = f"review-{request.review_id}-llm"
        self._ensure_secret(
            core,
            namespace=namespace,
            name=git_secret_name,
            data=request.resolved_secret_env,
            keys_filter=_git_secret_keys(request),
        )
        self._ensure_secret(
            core,
            namespace=namespace,
            name=llm_secret_name,
            data=request.resolved_secret_env,
            keys_filter=_llm_secret_keys(),
        )

        exec_request = request.model_copy(
            update={
                "credentials": request.credentials.model_copy(
                    update={
                        "git_credential_ref": SecretRef(
                            name=git_secret_name,
                            key="credentials",
                            namespace=namespace,
                        ),
                        "llm_credential_ref": SecretRef(
                            name=llm_secret_name,
                            key="credentials",
                            namespace=namespace,
                        ),
                    }
                )
            }
        )

        k8s_spec = build_kubernetes_execution_spec(
            exec_request,
            agent_image=self._agent_image,
            namespace=namespace,
        )
        run_spec = build_cogito_review_run_spec(k8s_spec)
        body = {
            "apiVersion": f"{COGITO_REVIEW_RUN_GROUP}/{COGITO_REVIEW_RUN_VERSION}",
            "kind": "CogitoReviewRun",
            "metadata": {"name": run_name, "namespace": namespace},
            "spec": cogito_review_run_spec_to_crd(run_spec),
        }

        try:
            api.create_namespaced_custom_object(
                group=COGITO_REVIEW_RUN_GROUP,
                version=COGITO_REVIEW_RUN_VERSION,
                namespace=namespace,
                plural=COGITO_REVIEW_RUN_PLURAL,
                body=body,
            )
        except client.ApiException as exc:
            if exc.status != 409:
                raise
            api.patch_namespaced_custom_object(
                group=COGITO_REVIEW_RUN_GROUP,
                version=COGITO_REVIEW_RUN_VERSION,
                namespace=namespace,
                plural=COGITO_REVIEW_RUN_PLURAL,
                name=run_name,
                body=body,
            )

    @staticmethod
    def _ensure_secret(
        core: Any,
        *,
        namespace: str,
        name: str,
        data: dict[str, str],
        keys_filter: set[str],
    ) -> None:
        import base64

        from kubernetes import client

        encoded = {
            "credentials": base64.b64encode(
                _encode_credential_blob(data, keys_filter).encode("utf-8")
            ).decode("ascii")
        }
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            data=encoded,
        )
        try:
            core.create_namespaced_secret(namespace=namespace, body=secret)
        except client.ApiException as exc:
            if exc.status != 409:
                raise
            core.patch_namespaced_secret(
                name=name,
                namespace=namespace,
                body=secret,
            )


def _encode_credential_blob(data: dict[str, str], keys: set[str]) -> str:
    import json

    return json.dumps({k: data[k] for k in sorted(keys) if k in data and data[k]})


def _git_secret_keys(request: ReviewExecutionRequest) -> set[str]:
    provider = request.review.git_provider
    if provider == "github":
        return {"COGITO_REVIEW_GITHUB_TOKEN"}
    if provider == "gitlab":
        return {"COGITO_REVIEW_GITLAB_TOKEN", "COGITO_REVIEW_GITLAB_BASE_URL"}
    if provider == "bitbucket":
        return {"COGITO_REVIEW_BITBUCKET_TOKEN"}
    if provider == "bitbucket-dc":
        return {
            "COGITO_REVIEW_BITBUCKET_DC_TOKEN",
            "COGITO_REVIEW_BITBUCKET_DC_BASE_URL",
        }
    return {
        "COGITO_REVIEW_ADO_PAT",
        "COGITO_REVIEW_ADO_ORGANIZATION",
        "COGITO_REVIEW_ADO_PROJECT",
    }


def _llm_secret_keys() -> set[str]:
    return {"COGITO_REVIEW_LLM_API_TOKEN", "COGITO_REVIEW_CALLBACK_SECRET"}
