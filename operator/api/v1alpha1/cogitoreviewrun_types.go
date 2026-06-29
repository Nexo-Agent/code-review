/*
Copyright 2026 CogitoForge AI.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// Package v1alpha1 contains API Schema definitions for the platform v1alpha1 API group.
package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// SecretRef references a key in a Kubernetes Secret.
type SecretRef struct {
	Name      string `json:"name"`
	Key       string `json:"key"`
	Namespace string `json:"namespace,omitempty"`
}

// ResourceRef references another namespaced custom resource.
type ResourceRef struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace,omitempty"`
}

// CogitoReviewRunReview identifies the product review record.
type CogitoReviewRunReview struct {
	ReviewID     string `json:"reviewId"`
	RepoFullName string `json:"repoFullName"`
	PRNumber     int32  `json:"prNumber"`
	HeadSHA      string `json:"headSha"`
}

// CallbackSpec configures agent callback delivery.
type CallbackSpec struct {
	Mode      string    `json:"mode"`
	URL       string    `json:"url"`
	SecretRef SecretRef `json:"secretRef"`
}

// WorkspaceSpec configures repository workspace preparation.
type WorkspaceSpec struct {
	Strategy string `json:"strategy"`
	RootPath string `json:"rootPath"`
}

// CredentialRefs references secrets holding provider credentials.
type CredentialRefs struct {
	GitCredentialRef SecretRef `json:"gitCredentialRef"`
	LLMCredentialRef SecretRef `json:"llmCredentialRef"`
}

// KubernetesExecutionInnerSpec is the kubernetes execution payload.
type KubernetesExecutionInnerSpec struct {
	AgentImage  string            `json:"agentImage"`
	Callback    CallbackSpec      `json:"callback"`
	Workspace   WorkspaceSpec     `json:"workspace"`
	Credentials CredentialRefs    `json:"credentials"`
	Environment map[string]string `json:"environment,omitempty"`
}

// CogitoReviewRunExecution wraps the execution backend spec.
type CogitoReviewRunExecution struct {
	Kind string                       `json:"kind"`
	Spec KubernetesExecutionInnerSpec `json:"spec"`
}

// CogitoReviewRunSpec defines the desired state of CogitoReviewRun.
type CogitoReviewRunSpec struct {
	InstallationRef  *ResourceRef             `json:"installationRef,omitempty"`
	RuntimePolicyRef *ResourceRef             `json:"runtimePolicyRef,omitempty"`
	ScalingPolicyRef *ResourceRef             `json:"scalingPolicyRef,omitempty"`
	Review           CogitoReviewRunReview    `json:"review"`
	Execution        CogitoReviewRunExecution `json:"execution"`
	Config           map[string]string        `json:"config,omitempty"`
}

// Condition describes an operator condition.
type Condition struct {
	Type               string `json:"type"`
	Status             string `json:"status"`
	Reason             string `json:"reason,omitempty"`
	Message            string `json:"message,omitempty"`
	LastTransitionTime string `json:"lastTransitionTime,omitempty"`
}

// CogitoReviewRunStatus defines the observed state of CogitoReviewRun.
type CogitoReviewRunStatus struct {
	Phase            string      `json:"phase,omitempty"`
	Conditions       []Condition `json:"conditions,omitempty"`
	SelectedExecutor string      `json:"selectedExecutor,omitempty"`
	JobRef           string      `json:"jobRef,omitempty"`
	PodRefs          []string    `json:"podRefs,omitempty"`
	StartedAt        string      `json:"startedAt,omitempty"`
	CompletedAt      string      `json:"completedAt,omitempty"`
	ExitCode         *int32      `json:"exitCode,omitempty"`
	FailureReason    string      `json:"failureReason,omitempty"`
	CallbackObserved bool        `json:"callbackObserved,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=crr

// CogitoReviewRun is the Schema for the cogitoreviewruns API.
type CogitoReviewRun struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   CogitoReviewRunSpec   `json:"spec,omitempty"`
	Status CogitoReviewRunStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// CogitoReviewRunList contains a list of CogitoReviewRun.
type CogitoReviewRunList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []CogitoReviewRun `json:"items"`
}

func init() {
	SchemeBuilder.Register(&CogitoReviewRun{}, &CogitoReviewRunList{})
}
