/*
Copyright 2026 CogitoForge AI.
*/

package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// JobCleanupSpec controls stale Job deletion.
type JobCleanupSpec struct {
	DeleteFailedJobsAfterSeconds    int32 `json:"deleteFailedJobsAfterSeconds,omitempty"`
	DeleteSucceededJobsAfterSeconds int32 `json:"deleteSucceededJobsAfterSeconds,omitempty"`
}

// JobPolicySpec configures review agent Jobs.
type JobPolicySpec struct {
	TTLSecondsAfterFinished int32          `json:"ttlSecondsAfterFinished,omitempty"`
	BackoffLimit            int32          `json:"backoffLimit,omitempty"`
	ActiveDeadlineSeconds   int32          `json:"activeDeadlineSeconds,omitempty"`
	Cleanup                 JobCleanupSpec `json:"cleanup,omitempty"`
}

// ExecutorSpec selects the Kubernetes executor.
type ExecutorSpec struct {
	Type               string   `json:"type"`
	Namespace          string   `json:"namespace"`
	ServiceAccountName string   `json:"serviceAccountName,omitempty"`
	ImagePullSecrets   []string `json:"imagePullSecrets,omitempty"`
}

// ResourceRequirements mirrors core resource requirements.
type ResourceRequirements struct {
	CPU    string `json:"cpu,omitempty"`
	Memory string `json:"memory,omitempty"`
}

// ResourcePair groups requests and limits.
type ResourcePair struct {
	Requests ResourceRequirements `json:"requests,omitempty"`
	Limits   ResourceRequirements `json:"limits,omitempty"`
}

// ExecutionPolicySpec configures review execution timeout.
type ExecutionPolicySpec struct {
	TimeoutSeconds int32 `json:"timeoutSeconds,omitempty"`
}

// CogitoReviewRuntimePolicySpec defines runtime execution policy.
type CogitoReviewRuntimePolicySpec struct {
	Executor  ExecutorSpec        `json:"executor"`
	Job       JobPolicySpec       `json:"job,omitempty"`
	Resources ResourcePair        `json:"resources,omitempty"`
	Execution ExecutionPolicySpec `json:"execution,omitempty"`
}

// CogitoReviewRuntimePolicyStatus reports policy readiness.
type CogitoReviewRuntimePolicyStatus struct {
	Conditions             []Condition `json:"conditions,omitempty"`
	EffectiveExecutor      string      `json:"effectiveExecutor,omitempty"`
	ResolvedServiceAccount string      `json:"resolvedServiceAccount,omitempty"`
	ResolvedNamespace      string      `json:"resolvedNamespace,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status

type CogitoReviewRuntimePolicy struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   CogitoReviewRuntimePolicySpec   `json:"spec,omitempty"`
	Status CogitoReviewRuntimePolicyStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

type CogitoReviewRuntimePolicyList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []CogitoReviewRuntimePolicy `json:"items"`
}

func init() {
	SchemeBuilder.Register(&CogitoReviewRuntimePolicy{}, &CogitoReviewRuntimePolicyList{})
}
