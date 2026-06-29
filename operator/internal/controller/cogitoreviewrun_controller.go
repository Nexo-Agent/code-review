package controller

import (
	"context"
	"fmt"
	"time"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/util/retry"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
	jobbuilder "github.com/cogitoforge-ai/cogito-review/operator/internal/job"
	"github.com/cogitoforge-ai/cogito-review/operator/internal/secrets"
)

const runFinalizer = "platform.cogito.review/finalizer"

// CogitoReviewRunReconciler reconciles a CogitoReviewRun object.
type CogitoReviewRunReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewruns,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewruns/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewruns/finalizers,verbs=update
// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewruntimepolicies,verbs=get;list;watch
// +kubebuilder:rbac:groups=batch,resources=jobs,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=secrets,verbs=get;list;watch
// +kubebuilder:rbac:groups="",resources=pods,verbs=get;list;watch

func (r *CogitoReviewRunReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	var run platformv1alpha1.CogitoReviewRun
	if err := r.Get(ctx, req.NamespacedName, &run); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if run.DeletionTimestamp != nil {
		return r.finalize(ctx, &run)
	}

	if !controllerutil.ContainsFinalizer(&run, runFinalizer) {
		if err := r.addFinalizer(ctx, client.ObjectKeyFromObject(&run)); err != nil {
			return ctrl.Result{}, err
		}
		return ctrl.Result{Requeue: true}, nil
	}

	if err := validateRunSpec(&run); err != nil {
		return r.setFailed(ctx, &run, err.Error())
	}

	policy, err := r.resolveRuntimePolicy(ctx, &run)
	if err != nil {
		return r.setFailed(ctx, &run, err.Error())
	}

	env, err := r.buildAgentEnv(ctx, &run)
	if err != nil {
		return r.setFailed(ctx, &run, err.Error())
	}

	desiredJob := jobbuilder.BuildAgentJob(&run, env, policy)
	var existing batchv1.Job
	jobKey := client.ObjectKeyFromObject(desiredJob)
	if err := r.Get(ctx, jobKey, &existing); err != nil {
		if !apierrors.IsNotFound(err) {
			return ctrl.Result{}, err
		}
		if err := r.Create(ctx, desiredJob); err != nil {
			return ctrl.Result{}, err
		}
		logger.Info("created review agent job", "job", desiredJob.Name)
		if err := r.updateRunStatus(ctx, client.ObjectKeyFromObject(&run), func(status *platformv1alpha1.CogitoReviewRunStatus) {
			status.Phase = "Scheduled"
			status.SelectedExecutor = "kubernetes-job"
			status.JobRef = fmt.Sprintf("%s/%s", desiredJob.Namespace, desiredJob.Name)
			setCondition(&status.Conditions, "JobCreated", "True", "JobCreated", "review agent job created")
		}); err != nil {
			return ctrl.Result{}, err
		}
		return ctrl.Result{RequeueAfter: 5 * time.Second}, nil
	}

	return r.observeJob(ctx, &run, &existing, policy)
}

func validateRunSpec(run *platformv1alpha1.CogitoReviewRun) error {
	if run.Spec.Review.ReviewID == "" {
		return fmt.Errorf("spec.review.reviewId is required")
	}
	if run.Spec.Execution.Kind != "kubernetes" {
		return fmt.Errorf("unsupported execution kind %q", run.Spec.Execution.Kind)
	}
	if run.Spec.Execution.Spec.AgentImage == "" {
		return fmt.Errorf("spec.execution.spec.agentImage is required")
	}
	return nil
}

func (r *CogitoReviewRunReconciler) resolveRuntimePolicy(
	ctx context.Context,
	run *platformv1alpha1.CogitoReviewRun,
) (*platformv1alpha1.CogitoReviewRuntimePolicy, error) {
	if run.Spec.RuntimePolicyRef == nil || run.Spec.RuntimePolicyRef.Name == "" {
		return jobbuilder.DefaultRuntimePolicy(run.Namespace), nil
	}
	ns := run.Spec.RuntimePolicyRef.Namespace
	if ns == "" {
		ns = run.Namespace
	}
	var policy platformv1alpha1.CogitoReviewRuntimePolicy
	if err := r.Get(ctx, client.ObjectKey{Name: run.Spec.RuntimePolicyRef.Name, Namespace: ns}, &policy); err != nil {
		return nil, fmt.Errorf("resolve runtime policy: %w", err)
	}
	return &policy, nil
}

func (r *CogitoReviewRunReconciler) buildAgentEnv(
	ctx context.Context,
	run *platformv1alpha1.CogitoReviewRun,
) (map[string]string, error) {
	spec := run.Spec.Execution.Spec
	env := map[string]string{}

	gitEnv, err := secrets.ResolveCredentialBlob(ctx, r.Client, run.Namespace, spec.Credentials.GitCredentialRef)
	if err != nil {
		return nil, err
	}
	llmEnv, err := secrets.ResolveCredentialBlob(ctx, r.Client, run.Namespace, spec.Credentials.LLMCredentialRef)
	if err != nil {
		return nil, err
	}
	callbackSecret, err := secrets.ResolveSecretKey(ctx, r.Client, run.Namespace, spec.Callback.SecretRef)
	if err != nil {
		return nil, err
	}

	for k, v := range gitEnv {
		env[k] = v
	}
	for k, v := range llmEnv {
		env[k] = v
	}
	env["COGITO_REVIEW_CALLBACK_URL"] = spec.Callback.URL
	env["COGITO_REVIEW_CALLBACK_SECRET"] = callbackSecret
	env["COGITO_REVIEW_REVIEW_ID"] = run.Spec.Review.ReviewID
	return env, nil
}

func (r *CogitoReviewRunReconciler) observeJob(
	ctx context.Context,
	run *platformv1alpha1.CogitoReviewRun,
	job *batchv1.Job,
	policy *platformv1alpha1.CogitoReviewRuntimePolicy,
) (ctrl.Result, error) {
	run.Status.JobRef = fmt.Sprintf("%s/%s", job.Namespace, job.Name)

	if job.Status.StartTime != nil && run.Status.StartedAt == "" {
		run.Status.StartedAt = job.Status.StartTime.UTC().Format(time.RFC3339)
	}

	for _, cond := range job.Status.Conditions {
		if cond.Type == batchv1.JobComplete && cond.Status == corev1.ConditionTrue {
			completedAt := time.Now().UTC().Format(time.RFC3339)
			exit := int32(0)
			jobRef := fmt.Sprintf("%s/%s", job.Namespace, job.Name)
			startedAt := ""
			if job.Status.StartTime != nil {
				startedAt = job.Status.StartTime.UTC().Format(time.RFC3339)
			}
			if err := r.updateRunStatus(ctx, client.ObjectKeyFromObject(run), func(status *platformv1alpha1.CogitoReviewRunStatus) {
				status.JobRef = jobRef
				if status.StartedAt == "" && startedAt != "" {
					status.StartedAt = startedAt
				}
				status.Phase = "Succeeded"
				status.CompletedAt = completedAt
				status.ExitCode = &exit
				setCondition(&status.Conditions, "JobCompleted", "True", "Succeeded", "review agent job succeeded")
			}); err != nil {
				return ctrl.Result{}, err
			}
			return r.maybeCleanupJob(ctx, job, policy, true)
		}
		if cond.Type == batchv1.JobFailed && cond.Status == corev1.ConditionTrue {
			completedAt := time.Now().UTC().Format(time.RFC3339)
			exit := int32(1)
			jobRef := fmt.Sprintf("%s/%s", job.Namespace, job.Name)
			startedAt := ""
			if job.Status.StartTime != nil {
				startedAt = job.Status.StartTime.UTC().Format(time.RFC3339)
			}
			failureReason := cond.Message
			if cond.Reason != "" {
				failureReason = cond.Reason
			}
			if err := r.updateRunStatus(ctx, client.ObjectKeyFromObject(run), func(status *platformv1alpha1.CogitoReviewRunStatus) {
				status.JobRef = jobRef
				if status.StartedAt == "" && startedAt != "" {
					status.StartedAt = startedAt
				}
				status.Phase = "Failed"
				status.CompletedAt = completedAt
				status.FailureReason = failureReason
				status.ExitCode = &exit
				setCondition(&status.Conditions, "JobCompleted", "True", "Failed", failureReason)
			}); err != nil {
				return ctrl.Result{}, err
			}
			return r.maybeCleanupJob(ctx, job, policy, false)
		}
	}

	jobRef := fmt.Sprintf("%s/%s", job.Namespace, job.Name)
	startedAt := ""
	if job.Status.StartTime != nil {
		startedAt = job.Status.StartTime.UTC().Format(time.RFC3339)
	}
	if err := r.updateRunStatus(ctx, client.ObjectKeyFromObject(run), func(status *platformv1alpha1.CogitoReviewRunStatus) {
		status.JobRef = jobRef
		if status.StartedAt == "" && startedAt != "" {
			status.StartedAt = startedAt
		}
		if job.Status.Active > 0 {
			status.Phase = "Running"
			setCondition(&status.Conditions, "JobCreated", "True", "Running", "review agent job is running")
		} else if status.Phase == "" {
			status.Phase = "Pending"
		}
	}); err != nil {
		return ctrl.Result{}, err
	}
	return ctrl.Result{RequeueAfter: 10 * time.Second}, nil
}

func (r *CogitoReviewRunReconciler) maybeCleanupJob(
	ctx context.Context,
	job *batchv1.Job,
	policy *platformv1alpha1.CogitoReviewRuntimePolicy,
	succeeded bool,
) (ctrl.Result, error) {
	delay := int32(3600)
	if policy != nil {
		if succeeded && policy.Spec.Job.Cleanup.DeleteSucceededJobsAfterSeconds > 0 {
			delay = policy.Spec.Job.Cleanup.DeleteSucceededJobsAfterSeconds
		}
		if !succeeded && policy.Spec.Job.Cleanup.DeleteFailedJobsAfterSeconds > 0 {
			delay = policy.Spec.Job.Cleanup.DeleteFailedJobsAfterSeconds
		}
	}
	if delay == 0 {
		return ctrl.Result{}, nil
	}
	return ctrl.Result{RequeueAfter: time.Duration(delay) * time.Second}, nil
}

func (r *CogitoReviewRunReconciler) setFailed(
	ctx context.Context,
	run *platformv1alpha1.CogitoReviewRun,
	reason string,
) (ctrl.Result, error) {
	if err := r.updateRunStatus(ctx, client.ObjectKeyFromObject(run), func(status *platformv1alpha1.CogitoReviewRunStatus) {
		status.Phase = "Failed"
		status.FailureReason = reason
		setCondition(&status.Conditions, "Ready", "False", "ValidationFailed", reason)
	}); err != nil {
		return ctrl.Result{}, err
	}
	return ctrl.Result{}, nil
}

func (r *CogitoReviewRunReconciler) finalize(ctx context.Context, run *platformv1alpha1.CogitoReviewRun) (ctrl.Result, error) {
	if err := r.removeFinalizer(ctx, client.ObjectKeyFromObject(run)); err != nil {
		return ctrl.Result{}, err
	}
	return ctrl.Result{}, nil
}

func (r *CogitoReviewRunReconciler) addFinalizer(ctx context.Context, key client.ObjectKey) error {
	return retry.RetryOnConflict(retry.DefaultRetry, func() error {
		var latest platformv1alpha1.CogitoReviewRun
		if err := r.Get(ctx, key, &latest); err != nil {
			return err
		}
		if controllerutil.ContainsFinalizer(&latest, runFinalizer) {
			return nil
		}
		controllerutil.AddFinalizer(&latest, runFinalizer)
		return r.Update(ctx, &latest)
	})
}

func (r *CogitoReviewRunReconciler) removeFinalizer(ctx context.Context, key client.ObjectKey) error {
	return retry.RetryOnConflict(retry.DefaultRetry, func() error {
		var latest platformv1alpha1.CogitoReviewRun
		if err := r.Get(ctx, key, &latest); err != nil {
			return client.IgnoreNotFound(err)
		}
		if !controllerutil.ContainsFinalizer(&latest, runFinalizer) {
			return nil
		}
		controllerutil.RemoveFinalizer(&latest, runFinalizer)
		return r.Update(ctx, &latest)
	})
}

func (r *CogitoReviewRunReconciler) updateRunStatus(
	ctx context.Context,
	key client.ObjectKey,
	mutate func(status *platformv1alpha1.CogitoReviewRunStatus),
) error {
	return retry.RetryOnConflict(retry.DefaultRetry, func() error {
		var latest platformv1alpha1.CogitoReviewRun
		if err := r.Get(ctx, key, &latest); err != nil {
			return err
		}
		mutate(&latest.Status)
		return r.Status().Update(ctx, &latest)
	})
}

func setCondition(conditions *[]platformv1alpha1.Condition, typ, status, reason, message string) {
	now := time.Now().UTC().Format(time.RFC3339)
	for i := range *conditions {
		if (*conditions)[i].Type == typ {
			(*conditions)[i].Status = status
			(*conditions)[i].Reason = reason
			(*conditions)[i].Message = message
			(*conditions)[i].LastTransitionTime = now
			return
		}
	}
	*conditions = append(*conditions, platformv1alpha1.Condition{
		Type:               typ,
		Status:             status,
		Reason:             reason,
		Message:            message,
		LastTransitionTime: now,
	})
}

func (r *CogitoReviewRunReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&platformv1alpha1.CogitoReviewRun{}).
		Owns(&batchv1.Job{}).
		Complete(r)
}
