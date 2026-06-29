package controller

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
	jobbuilder "github.com/cogitoforge-ai/cogito-review/operator/internal/job"
)

const installationFinalizer = "platform.cogito.review/installation-finalizer"

// CogitoReviewInstallationReconciler reconciles a CogitoReviewInstallation object.
type CogitoReviewInstallationReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewinstallations,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewinstallations/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=platform.cogito.review,resources=cogitoreviewinstallations/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=batch,resources=jobs,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=secrets,verbs=get;list;watch
// +kubebuilder:rbac:groups=networking.k8s.io,resources=ingresses,verbs=get;list;watch;create;update;patch;delete

func (r *CogitoReviewInstallationReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	var install platformv1alpha1.CogitoReviewInstallation
	if err := r.Get(ctx, req.NamespacedName, &install); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if install.DeletionTimestamp != nil {
		controllerutil.RemoveFinalizer(&install, installationFinalizer)
		return ctrl.Result{}, r.Update(ctx, &install)
	}

	if !controllerutil.ContainsFinalizer(&install, installationFinalizer) {
		controllerutil.AddFinalizer(&install, installationFinalizer)
		if err := r.Update(ctx, &install); err != nil {
			return ctrl.Result{}, err
		}
		return ctrl.Result{Requeue: true}, nil
	}

	apiReplicas := int32(1)
	workerReplicas := int32(1)
	if install.Spec.Components.API.Replicas > 0 {
		apiReplicas = install.Spec.Components.API.Replicas
	}
	if install.Spec.Components.Worker.Replicas > 0 {
		workerReplicas = install.Spec.Components.Worker.Replicas
	}

	commonEnv := r.buildCommonEnv(&install)
	resources := []client.Object{
		r.buildMigrateJob(&install, commonEnv),
		r.buildAPIDeployment(&install, commonEnv, apiReplicas),
		r.buildWorkerDeployment(&install, commonEnv, workerReplicas),
		jobbuilder.ServiceForComponent("cogito-review-api", install.Namespace, 8000, map[string]string{
			"app.kubernetes.io/name":      "cogito-review",
			"app.kubernetes.io/component": "api",
		}),
	}

	if install.Spec.Ingress.Enabled {
		resources = append(resources, r.buildIngress(&install))
	}

	for _, obj := range resources {
		obj.SetNamespace(install.Namespace)
		if err := controllerutil.SetControllerReference(&install, obj, r.Scheme); err != nil {
			return ctrl.Result{}, err
		}
		if err := r.applyObject(ctx, obj); err != nil {
			return ctrl.Result{}, err
		}
	}

	install.Status.Phase = "Ready"
	install.Status.ObservedGeneration = install.Generation
	install.Status.ObservedVersion = install.Spec.Version
	install.Status.AvailableComponents = []string{"api", "worker", "migrate"}
	install.Status.Endpoints = []platformv1alpha1.EndpointStatus{
		{Name: "api", URL: fmt.Sprintf("http://cogito-review-api.%s.svc:8000", install.Namespace)},
	}
	setCondition(&install.Status.Conditions, "Ready", "True", "Reconciled", "installation reconciled")
	if err := r.Status().Update(ctx, &install); err != nil {
		return ctrl.Result{}, err
	}

	logger.Info("reconciled installation", "name", install.Name)
	return ctrl.Result{}, nil
}

func (r *CogitoReviewInstallationReconciler) applyObject(ctx context.Context, obj client.Object) error {
	key := client.ObjectKeyFromObject(obj)
	existing := obj.DeepCopyObject().(client.Object)
	if err := r.Get(ctx, key, existing); err != nil {
		if apierrors.IsNotFound(err) {
			return r.Create(ctx, obj)
		}
		return err
	}
	obj.SetResourceVersion(existing.GetResourceVersion())
	return r.Update(ctx, obj)
}

func (r *CogitoReviewInstallationReconciler) buildCommonEnv(install *platformv1alpha1.CogitoReviewInstallation) []corev1.EnvVar {
	env := []corev1.EnvVar{
		envFromSecret("DATABASE_URL", install.Spec.Database.URLSecretRef),
		envFromSecret("COGITO_REVIEW_CELERY_BROKER_URL", install.Spec.Redis.URLSecretRef),
		envFromSecret("COGITO_REVIEW_AGENT_CALLBACK_SECRET", install.Spec.Secrets.CallbackSecretRef),
		envFromSecret("COGITO_REVIEW_SESSION_SECRET", install.Spec.Secrets.SessionSecretRef),
		envFromSecret("COGITO_REVIEW_SECRETS_ENCRYPTION_KEY", install.Spec.Secrets.EncryptionKeySecretRef),
		{Name: "COGITO_REVIEW_AGENT_CALLBACK_URL", Value: fmt.Sprintf("http://cogito-review-api.%s.svc:8000/api/v1/agent/review-events", install.Namespace)},
		{Name: "COGITO_REVIEW_RUNTIME_PROVIDER", Value: "k8s"},
		{Name: "COGITO_REVIEW_K8S_RUN_NAMESPACE", Value: install.Namespace},
		{Name: "COGITO_REVIEW_K8S_INSTALLATION_REF", Value: install.Name},
		{Name: "COGITO_REVIEW_AGENT_IMAGE", Value: install.Spec.Images.Agent},
	}
	if install.Spec.Frontend.PublicURL != "" {
		env = append(env, corev1.EnvVar{Name: "COGITO_REVIEW_FRONTEND_URL", Value: install.Spec.Frontend.PublicURL})
	}
	if install.Spec.RuntimePolicyRef != "" {
		env = append(env, corev1.EnvVar{Name: "COGITO_REVIEW_K8S_RUNTIME_POLICY_REF", Value: install.Spec.RuntimePolicyRef})
	}
	if install.Spec.ScalingPolicyRef != "" {
		env = append(env, corev1.EnvVar{Name: "COGITO_REVIEW_K8S_SCALING_POLICY_REF", Value: install.Spec.ScalingPolicyRef})
	}
	if install.Spec.Auth.Enabled {
		env = append(env, corev1.EnvVar{Name: "COGITO_REVIEW_AUTH_ENABLED", Value: "true"})
	}
	return env
}

func envFromSecret(name string, ref platformv1alpha1.SecretRef) corev1.EnvVar {
	return corev1.EnvVar{
		Name: name,
		ValueFrom: &corev1.EnvVarSource{
			SecretKeyRef: &corev1.SecretKeySelector{
				LocalObjectReference: corev1.LocalObjectReference{Name: ref.Name},
				Key:                  ref.Key,
			},
		},
	}
}

func (r *CogitoReviewInstallationReconciler) buildAPIDeployment(
	install *platformv1alpha1.CogitoReviewInstallation,
	env []corev1.EnvVar,
	replicas int32,
) *appsv1.Deployment {
	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{Name: "cogito-review-api"},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app.kubernetes.io/name":      "cogito-review",
					"app.kubernetes.io/component": "api",
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app.kubernetes.io/name":      "cogito-review",
						"app.kubernetes.io/component": "api",
					},
				},
				Spec: corev1.PodSpec{
					ServiceAccountName: "cogito-review-api",
					Containers: []corev1.Container{
						{
							Name:  "api",
							Image: install.Spec.Images.App,
							Ports: []corev1.ContainerPort{{ContainerPort: 8000}},
							Env:   env,
						},
					},
				},
			},
		},
	}
}

func (r *CogitoReviewInstallationReconciler) buildWorkerDeployment(
	install *platformv1alpha1.CogitoReviewInstallation,
	env []corev1.EnvVar,
	replicas int32,
) *appsv1.Deployment {
	workerEnv := append([]corev1.EnvVar{}, env...)
	workerEnv = append(workerEnv,
		corev1.EnvVar{Name: "COGITO_REVIEW_WORKSPACE_ROOT", Value: "/workspaces"},
		corev1.EnvVar{Name: "COGITO_REVIEW_RUNTIME_PROVIDER", Value: "k8s"},
	)
	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{Name: "cogito-review-worker"},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app.kubernetes.io/name":      "cogito-review",
					"app.kubernetes.io/component": "worker",
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app.kubernetes.io/name":      "cogito-review",
						"app.kubernetes.io/component": "worker",
					},
				},
				Spec: corev1.PodSpec{
					ServiceAccountName: "cogito-review-worker",
					Containers: []corev1.Container{
						{
							Name:    "worker",
							Image:   install.Spec.Images.App,
							Command: []string{"cogito-review", "job", "worker", "--concurrency", "1"},
							Env:     workerEnv,
						},
					},
				},
			},
		},
	}
}

func (r *CogitoReviewInstallationReconciler) buildMigrateJob(
	install *platformv1alpha1.CogitoReviewInstallation,
	env []corev1.EnvVar,
) *batchv1.Job {
	backoff := int32(1)
	return &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{Name: "cogito-review-migrate"},
		Spec: batchv1.JobSpec{
			BackoffLimit: &backoff,
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:    "migrate",
							Image:   install.Spec.Images.App,
							Command: []string{"dbmate", "-d", "/app/migrations", "--wait", "up"},
							Env:     env,
						},
					},
				},
			},
		},
	}
}

func (r *CogitoReviewInstallationReconciler) buildIngress(
	install *platformv1alpha1.CogitoReviewInstallation,
) *networkingv1.Ingress {
	pathType := networkingv1.PathTypePrefix
	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{Name: "cogito-review"},
		Spec: networkingv1.IngressSpec{
			IngressClassName: strPtr(install.Spec.Ingress.ClassName),
			Rules: []networkingv1.IngressRule{
				{
					Host: install.Spec.Ingress.Host,
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								{
									Path:     "/",
									PathType: &pathType,
									Backend: networkingv1.IngressBackend{
										Service: &networkingv1.IngressServiceBackend{
											Name: "cogito-review-api",
											Port: networkingv1.ServiceBackendPort{Number: 8000},
										},
									},
								},
							},
						},
					},
				},
			},
		},
	}
	if install.Spec.Ingress.TLSSecretRef != nil {
		ingress.Spec.TLS = []networkingv1.IngressTLS{
			{
				Hosts:      []string{install.Spec.Ingress.Host},
				SecretName: install.Spec.Ingress.TLSSecretRef.Name,
			},
		}
	}
	return ingress
}

func strPtr(v string) *string {
	if v == "" {
		return nil
	}
	return &v
}

func (r *CogitoReviewInstallationReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&platformv1alpha1.CogitoReviewInstallation{}).
		Owns(&appsv1.Deployment{}).
		Owns(&batchv1.Job{}).
		Owns(&corev1.Service{}).
		Owns(&networkingv1.Ingress{}).
		Complete(r)
}

// Ensure intstr import is used for future probes.
var _ = intstr.FromInt32
