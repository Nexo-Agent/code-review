"""Execution contract models (schema v1).

JSON Schemas in this directory:
- review-execution-request-v1.schema.json
- kubernetes-execution-spec-v1.schema.json
- cogito-review-run-v1.schema.json
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SecretRef(BaseModel):
    name: str
    key: str
    namespace: str = ""


class ReviewContext(BaseModel):
    repo_full_name: str
    pr_number: int
    head_sha: str
    git_provider: str


class CallbackConfig(BaseModel):
    url: str
    secret_ref: SecretRef
    metadata: dict[str, str] = Field(default_factory=dict)


class ExecutionConfig(BaseModel):
    workspace_root: str
    opencode_agent: str
    opencode_log_level: str = "INFO"
    review_timeout_seconds: int = 600
    system_prompt: str = ""
    llm_provider_id: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    opencode_model: str = ""


class CredentialRefs(BaseModel):
    git_credential_ref: SecretRef
    llm_credential_ref: SecretRef


class RuntimeMetadata(BaseModel):
    installation_ref: str = "main"
    runtime_policy_ref: str = "default"
    scaling_policy_ref: str = "default"
    namespace: str = ""


class ReviewExecutionRequest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    review_id: str
    review: ReviewContext
    callback: CallbackConfig
    config: ExecutionConfig
    credentials: CredentialRefs
    runtime_metadata: RuntimeMetadata = Field(default_factory=RuntimeMetadata)
    resolved_secret_env: dict[str, str] = Field(default_factory=dict, exclude=True)


class WorkspaceSpec_K8s(BaseModel):
    strategy: Literal["ephemeral-clone"] = "ephemeral-clone"
    root_path: str = "/workspaces"


class CallbackSpec_K8s(BaseModel):
    mode: Literal["internal-service", "external"] = "internal-service"
    url: str
    secret_ref: SecretRef


class KubernetesExecutionSpec(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    review_id: str
    namespace: str
    installation_ref: str = "main"
    runtime_policy_ref: str = "default"
    scaling_policy_ref: str = "default"
    agent_image: str
    callback: CallbackSpec_K8s
    workspace: WorkspaceSpec_K8s = Field(default_factory=WorkspaceSpec_K8s)
    credentials: CredentialRefs
    environment: dict[str, str] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, str] = Field(default_factory=dict)


class ResourceRef(BaseModel):
    name: str
    namespace: str = ""


class CogitoReviewRunExecutionSpec(BaseModel):
    agent_image: str
    callback: CallbackSpec_K8s
    workspace: WorkspaceSpec_K8s = Field(default_factory=WorkspaceSpec_K8s)
    credentials: CredentialRefs
    environment: dict[str, str] = Field(default_factory=dict)


class CogitoReviewRunExecution(BaseModel):
    kind: Literal["kubernetes"] = "kubernetes"
    spec: CogitoReviewRunExecutionSpec


class CogitoReviewRunReview(BaseModel):
    review_id: str
    repo_full_name: str
    pr_number: int
    head_sha: str


class CogitoReviewRunSpec(BaseModel):
    installation_ref: ResourceRef | None = None
    runtime_policy_ref: ResourceRef | None = None
    scaling_policy_ref: ResourceRef | None = None
    review: CogitoReviewRunReview
    execution: CogitoReviewRunExecution
    config: dict[str, str] = Field(default_factory=dict)


class ExecutionSubmissionResult(BaseModel):
    backend_kind: Literal["docker", "kubernetes"]
    accepted: bool
    submitted_at: datetime
    external_ref: str = ""
    waits_for_completion: bool = False
