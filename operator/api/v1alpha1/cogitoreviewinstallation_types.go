/*
Copyright 2026 CogitoForge AI.
*/

package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ImageSpec pins application images.
type ImageSpec struct {
	App   string `json:"app"`
	Agent string `json:"agent"`
}

// IngressSpec configures optional HTTP ingress.
type IngressSpec struct {
	Enabled      bool       `json:"enabled"`
	ClassName    string     `json:"className,omitempty"`
	Host         string     `json:"host,omitempty"`
	TLSSecretRef *SecretRef `json:"tlsSecretRef,omitempty"`
}

// DatabaseSpec configures PostgreSQL connectivity.
type DatabaseSpec struct {
	Mode         string    `json:"mode"`
	URLSecretRef SecretRef `json:"urlSecretRef"`
}

// RedisSpec configures Redis connectivity.
type RedisSpec struct {
	Mode         string    `json:"mode"`
	URLSecretRef SecretRef `json:"urlSecretRef"`
}

// FrontendSpec configures public frontend URL.
type FrontendSpec struct {
	PublicURL string `json:"publicUrl"`
}

// InstallationSecretsSpec references installation-level secrets.
type InstallationSecretsSpec struct {
	CallbackSecretRef      SecretRef `json:"callbackSecretRef"`
	SessionSecretRef       SecretRef `json:"sessionSecretRef"`
	EncryptionKeySecretRef SecretRef `json:"encryptionKeySecretRef"`
}

// ComponentReplicaSpec configures component replica count override.
type ComponentReplicaSpec struct {
	Replicas int32 `json:"replicas,omitempty"`
}

// ComponentsSpec groups component overrides.
type ComponentsSpec struct {
	API    ComponentReplicaSpec `json:"api,omitempty"`
	Worker ComponentReplicaSpec `json:"worker,omitempty"`
}

// AuthSpec toggles product authentication.
type AuthSpec struct {
	Enabled bool `json:"enabled"`
}

// CogitoReviewInstallationSpec defines a managed installation.
type CogitoReviewInstallationSpec struct {
	Version          string                  `json:"version"`
	Images           ImageSpec               `json:"images"`
	Ingress          IngressSpec             `json:"ingress,omitempty"`
	Database         DatabaseSpec            `json:"database"`
	Redis            RedisSpec               `json:"redis"`
	Frontend         FrontendSpec            `json:"frontend,omitempty"`
	Auth             AuthSpec                `json:"auth,omitempty"`
	Secrets          InstallationSecretsSpec `json:"secrets"`
	RuntimePolicyRef string                  `json:"runtimePolicyRef,omitempty"`
	ScalingPolicyRef string                  `json:"scalingPolicyRef,omitempty"`
	Components       ComponentsSpec          `json:"components,omitempty"`
}

// EndpointStatus reports a service endpoint.
type EndpointStatus struct {
	Name string `json:"name"`
	URL  string `json:"url"`
}

// CogitoReviewInstallationStatus reports installation health.
type CogitoReviewInstallationStatus struct {
	Phase               string           `json:"phase,omitempty"`
	ObservedGeneration  int64            `json:"observedGeneration,omitempty"`
	ObservedVersion     string           `json:"observedVersion,omitempty"`
	Conditions          []Condition      `json:"conditions,omitempty"`
	Endpoints           []EndpointStatus `json:"endpoints,omitempty"`
	AvailableComponents []string         `json:"availableComponents,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status

type CogitoReviewInstallation struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   CogitoReviewInstallationSpec   `json:"spec,omitempty"`
	Status CogitoReviewInstallationStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

type CogitoReviewInstallationList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []CogitoReviewInstallation `json:"items"`
}

func init() {
	SchemeBuilder.Register(&CogitoReviewInstallation{}, &CogitoReviewInstallationList{})
}
