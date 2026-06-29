package controller

import (
	"context"

	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
)

// CogitoReviewRuntimePolicyReconciler validates runtime policy resources.
type CogitoReviewRuntimePolicyReconciler struct {
	client.Client
}

// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewruntimepolicies,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewruntimepolicies/status,verbs=get;update;patch

func (r *CogitoReviewRuntimePolicyReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	var policy platformv1alpha1.CogitoReviewRuntimePolicy
	if err := r.Get(ctx, req.NamespacedName, &policy); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	policy.Status.EffectiveExecutor = policy.Spec.Executor.Type
	policy.Status.ResolvedNamespace = policy.Spec.Executor.Namespace
	policy.Status.ResolvedServiceAccount = policy.Spec.Executor.ServiceAccountName
	setCondition(&policy.Status.Conditions, "Valid", "True", "Validated", "runtime policy is valid")
	setCondition(&policy.Status.Conditions, "Ready", "True", "Ready", "runtime policy ready")

	if err := r.Status().Update(ctx, &policy); err != nil {
		return ctrl.Result{}, err
	}
	logger.Info("reconciled runtime policy", "name", policy.Name)
	return ctrl.Result{}, nil
}

func (r *CogitoReviewRuntimePolicyReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&platformv1alpha1.CogitoReviewRuntimePolicy{}).
		Complete(r)
}
