package v1alpha1

import (
	"context"
	"fmt"

	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
)

// +kubebuilder:webhook:path=/validate-platform-cogito-review-v1alpha1-cogitoreviewrun,mutating=false,failurePolicy=fail,sideEffects=None,groups=platform.cogito.review,resources=cogitoreviewruns,verbs=create;update,versions=v1alpha1,name=vcogitoreviewrun.kb.io,admissionReviewVersions=v1

type CogitoReviewRunCustomValidator struct{}

var _ admission.CustomValidator = &CogitoReviewRunCustomValidator{}

func SetupCogitoReviewRunWebhookWithManager(mgr ctrl.Manager) error {
	return ctrl.NewWebhookManagedBy(mgr).
		For(&platformv1alpha1.CogitoReviewRun{}).
		WithValidator(&CogitoReviewRunCustomValidator{}).
		Complete()
}

func (v *CogitoReviewRunCustomValidator) ValidateCreate(_ context.Context, obj runtime.Object) (admission.Warnings, error) {
	run, ok := obj.(*platformv1alpha1.CogitoReviewRun)
	if !ok {
		return nil, fmt.Errorf("expected CogitoReviewRun")
	}
	return nil, validateRunAdmission(run)
}

func (v *CogitoReviewRunCustomValidator) ValidateUpdate(_ context.Context, _, newObj runtime.Object) (admission.Warnings, error) {
	run, ok := newObj.(*platformv1alpha1.CogitoReviewRun)
	if !ok {
		return nil, fmt.Errorf("expected CogitoReviewRun")
	}
	return nil, validateRunAdmission(run)
}

func (v *CogitoReviewRunCustomValidator) ValidateDelete(context.Context, runtime.Object) (admission.Warnings, error) {
	return nil, nil
}

func validateRunAdmission(run *platformv1alpha1.CogitoReviewRun) error {
	if run.Spec.Review.ReviewID == "" {
		return fmt.Errorf("spec.review.reviewId is required")
	}
	if run.Spec.Execution.Kind != "kubernetes" {
		return fmt.Errorf("only execution.kind=kubernetes is supported")
	}
	spec := run.Spec.Execution.Spec
	if spec.AgentImage == "" {
		return fmt.Errorf("spec.execution.spec.agentImage is required")
	}
	if spec.Callback.URL == "" {
		return fmt.Errorf("spec.execution.spec.callback.url is required")
	}
	if spec.Callback.SecretRef.Name == "" || spec.Callback.SecretRef.Key == "" {
		return fmt.Errorf("spec.execution.spec.callback.secretRef name and key are required")
	}
	if spec.Credentials.GitCredentialRef.Name == "" || spec.Credentials.LLMCredentialRef.Name == "" {
		return fmt.Errorf("credential secret references are required")
	}
	for _, value := range spec.Environment {
		if looksLikeSecret(value) {
			return fmt.Errorf("inline secret-like values are not allowed in spec.execution.spec.environment")
		}
	}
	return nil
}

func looksLikeSecret(value string) bool {
	if len(value) < 20 {
		return false
	}
	prefixes := []string{"ghp_", "gho_", "sk-", "xoxb-"}
	for _, p := range prefixes {
		if len(value) >= len(p) && value[:len(p)] == p {
			return true
		}
	}
	return false
}
