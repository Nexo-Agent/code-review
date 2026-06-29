/*
Copyright 2026 CogitoForge AI.
*/

package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// AutoscalingSpec configures HPA for a component.
type AutoscalingSpec struct {
	Enabled                        bool  `json:"enabled"`
	MinReplicas                    int32 `json:"minReplicas,omitempty"`
	MaxReplicas                    int32 `json:"maxReplicas,omitempty"`
	TargetCPUUtilizationPercentage int32 `json:"targetCPUUtilizationPercentage,omitempty"`
}

// ComponentScalingSpec configures replicas for a long-running component.
type ComponentScalingSpec struct {
	Replicas    int32           `json:"replicas,omitempty"`
	Autoscaling AutoscalingSpec `json:"autoscaling,omitempty"`
}

// WorkerConcurrencySpec configures worker throughput.
type WorkerConcurrencySpec struct {
	CeleryWorkerConcurrency   int32 `json:"celeryWorkerConcurrency,omitempty"`
	MaxQueuedReviewsPerWorker int32 `json:"maxQueuedReviewsPerWorker,omitempty"`
}

// WorkerScalingSpec configures the worker Deployment.
type WorkerScalingSpec struct {
	Replicas    int32                 `json:"replicas,omitempty"`
	Autoscaling AutoscalingSpec       `json:"autoscaling,omitempty"`
	Concurrency WorkerConcurrencySpec `json:"concurrency,omitempty"`
}

// ExecutionScalingSpec caps concurrent review Jobs.
type ExecutionScalingSpec struct {
	MaxConcurrentReviewJobs int32 `json:"maxConcurrentReviewJobs,omitempty"`
}

// CogitoReviewScalingPolicySpec defines scaling behavior.
type CogitoReviewScalingPolicySpec struct {
	API       ComponentScalingSpec `json:"api,omitempty"`
	Worker    WorkerScalingSpec    `json:"worker,omitempty"`
	Execution ExecutionScalingSpec `json:"execution,omitempty"`
}

// CogitoReviewScalingPolicyStatus reports effective scaling.
type CogitoReviewScalingPolicyStatus struct {
	Conditions           []Condition `json:"conditions,omitempty"`
	EffectiveReplicas    string      `json:"effectiveReplicas,omitempty"`
	EffectiveConcurrency string      `json:"effectiveConcurrency,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status

type CogitoReviewScalingPolicy struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   CogitoReviewScalingPolicySpec   `json:"spec,omitempty"`
	Status CogitoReviewScalingPolicyStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

type CogitoReviewScalingPolicyList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []CogitoReviewScalingPolicy `json:"items"`
}

func init() {
	SchemeBuilder.Register(&CogitoReviewScalingPolicy{}, &CogitoReviewScalingPolicyList{})
}
