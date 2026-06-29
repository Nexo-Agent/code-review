package controller

import (
	"context"
	"fmt"

	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
)

// CogitoReviewScalingPolicyReconciler validates scaling policy resources.
type CogitoReviewScalingPolicyReconciler struct {
	client.Client
}

// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewscalingpolicies,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewscalingpolicies/status,verbs=get;update;patch

func (r *CogitoReviewScalingPolicyReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	var policy platformv1alpha1.CogitoReviewScalingPolicy
	if err := r.Get(ctx, req.NamespacedName, &policy); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	policy.Status.EffectiveReplicas = fmt.Sprintf("api=%d worker=%d",
		maxInt32(policy.Spec.API.Replicas, 1),
		maxInt32(policy.Spec.Worker.Replicas, 1),
	)
	policy.Status.EffectiveConcurrency = fmt.Sprintf("maxJobs=%d celery=%d",
		maxInt32(policy.Spec.Execution.MaxConcurrentReviewJobs, 10),
		maxInt32(policy.Spec.Worker.Concurrency.CeleryWorkerConcurrency, 1),
	)
	setCondition(&policy.Status.Conditions, "Ready", "True", "Ready", "scaling policy ready")

	if err := r.Status().Update(ctx, &policy); err != nil {
		return ctrl.Result{}, err
	}
	logger.Info("reconciled scaling policy", "name", policy.Name)
	return ctrl.Result{}, nil
}

func maxInt32(v, fallback int32) int32 {
	if v > 0 {
		return v
	}
	return fallback
}

func (r *CogitoReviewScalingPolicyReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&platformv1alpha1.CogitoReviewScalingPolicy{}).
		Complete(r)
}
