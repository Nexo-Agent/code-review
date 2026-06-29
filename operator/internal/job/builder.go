package job

import (
	"fmt"
	"sort"
	"strconv"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/intstr"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
)

const (
	ReviewRoleLabel       = "nexo.coreview.role"
	ReviewIDLabel         = "nexo.coreview.review_id"
	ReviewAgentRole       = "review-agent"
	defaultTTLSeconds     = int32(3600)
	defaultBackoff        = int32(0)
	defaultActiveDeadline = int32(900)
)

// BuildAgentJob creates a one-shot Job for a CogitoReviewRun.
func BuildAgentJob(
	run *platformv1alpha1.CogitoReviewRun,
	env map[string]string,
	policy *platformv1alpha1.CogitoReviewRuntimePolicy,
) *batchv1.Job {
	spec := run.Spec.Execution.Spec
	jobName := fmt.Sprintf("review-%s", run.Spec.Review.ReviewID)

	ttl := defaultTTLSeconds
	backoff := defaultBackoff
	activeDeadline := int64(defaultActiveDeadline)
	serviceAccount := "cogito-review-agent"
	imagePullSecrets := []corev1.LocalObjectReference{}

	if policy != nil {
		if policy.Spec.Job.TTLSecondsAfterFinished > 0 {
			ttl = policy.Spec.Job.TTLSecondsAfterFinished
		}
		if policy.Spec.Job.BackoffLimit >= 0 {
			backoff = policy.Spec.Job.BackoffLimit
		}
		if policy.Spec.Job.ActiveDeadlineSeconds > 0 {
			activeDeadline = int64(policy.Spec.Job.ActiveDeadlineSeconds)
		}
		if policy.Spec.Executor.ServiceAccountName != "" {
			serviceAccount = policy.Spec.Executor.ServiceAccountName
		}
		for _, name := range policy.Spec.Executor.ImagePullSecrets {
			imagePullSecrets = append(imagePullSecrets, corev1.LocalObjectReference{Name: name})
		}
	}

	resources := corev1.ResourceRequirements{}
	if policy != nil {
		reqs := corev1.ResourceList{}
		limits := corev1.ResourceList{}
		if policy.Spec.Resources.Requests.CPU != "" {
			reqs[corev1.ResourceCPU] = resource.MustParse(policy.Spec.Resources.Requests.CPU)
		}
		if policy.Spec.Resources.Requests.Memory != "" {
			reqs[corev1.ResourceMemory] = resource.MustParse(policy.Spec.Resources.Requests.Memory)
		}
		if policy.Spec.Resources.Limits.CPU != "" {
			limits[corev1.ResourceCPU] = resource.MustParse(policy.Spec.Resources.Limits.CPU)
		}
		if policy.Spec.Resources.Limits.Memory != "" {
			limits[corev1.ResourceMemory] = resource.MustParse(policy.Spec.Resources.Limits.Memory)
		}
		if len(reqs) > 0 {
			resources.Requests = reqs
		}
		if len(limits) > 0 {
			resources.Limits = limits
		}
	}

	mergedMap := make(map[string]string, len(spec.Environment)+len(env))
	for k, v := range spec.Environment {
		mergedMap[k] = v
	}
	for k, v := range env {
		mergedMap[k] = v
	}
	keys := make([]string, 0, len(mergedMap))
	for k := range mergedMap {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	mergedEnv := make([]corev1.EnvVar, 0, len(keys))
	for _, k := range keys {
		mergedEnv = append(mergedEnv, corev1.EnvVar{Name: k, Value: mergedMap[k]})
	}

	workspaceRoot := spec.Workspace.RootPath
	if workspaceRoot == "" {
		workspaceRoot = "/workspaces"
	}

	podSpec := corev1.PodSpec{
		ServiceAccountName: serviceAccount,
		RestartPolicy:      corev1.RestartPolicyNever,
		ImagePullSecrets:   imagePullSecrets,
		Containers: []corev1.Container{
			{
				Name:            "agent",
				Image:           spec.AgentImage,
				ImagePullPolicy: corev1.PullIfNotPresent,
				Command: []string{
					"cogito-review-agent",
					"review",
					"run",
					"--review-id",
					run.Spec.Review.ReviewID,
				},
				Env:       mergedEnv,
				Resources: resources,
				VolumeMounts: []corev1.VolumeMount{
					{Name: "workspace", MountPath: workspaceRoot},
				},
			},
		},
		Volumes: []corev1.Volume{
			{
				Name: "workspace",
				VolumeSource: corev1.VolumeSource{
					EmptyDir: &corev1.EmptyDirVolumeSource{},
				},
			},
		},
	}

	return &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      jobName,
			Namespace: run.Namespace,
			Labels: map[string]string{
				ReviewRoleLabel: ReviewAgentRole,
				ReviewIDLabel:   run.Spec.Review.ReviewID,
			},
			OwnerReferences: []metav1.OwnerReference{
				*metav1.NewControllerRef(run, platformv1alpha1.GroupVersion.WithKind("CogitoReviewRun")),
			},
		},
		Spec: batchv1.JobSpec{
			TTLSecondsAfterFinished: &ttl,
			BackoffLimit:            &backoff,
			ActiveDeadlineSeconds:   &activeDeadline,
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						ReviewRoleLabel: ReviewAgentRole,
						ReviewIDLabel:   run.Spec.Review.ReviewID,
					},
				},
				Spec: podSpec,
			},
		},
	}
}

// DefaultRuntimePolicy returns baseline job execution policy.
func DefaultRuntimePolicy(namespace string) *platformv1alpha1.CogitoReviewRuntimePolicy {
	return &platformv1alpha1.CogitoReviewRuntimePolicy{
		Spec: platformv1alpha1.CogitoReviewRuntimePolicySpec{
			Executor: platformv1alpha1.ExecutorSpec{
				Type:               "kubernetes-job",
				Namespace:          namespace,
				ServiceAccountName: "cogito-review-agent",
			},
			Job: platformv1alpha1.JobPolicySpec{
				TTLSecondsAfterFinished: defaultTTLSeconds,
				BackoffLimit:            defaultBackoff,
				ActiveDeadlineSeconds:   defaultActiveDeadline,
				Cleanup: platformv1alpha1.JobCleanupSpec{
					DeleteFailedJobsAfterSeconds:    86400,
					DeleteSucceededJobsAfterSeconds: 3600,
				},
			},
			Resources: platformv1alpha1.ResourcePair{
				Requests: platformv1alpha1.ResourceRequirements{CPU: "500m", Memory: "1Gi"},
				Limits:   platformv1alpha1.ResourceRequirements{CPU: "1", Memory: "2Gi"},
			},
			Execution: platformv1alpha1.ExecutionPolicySpec{TimeoutSeconds: 600},
		},
	}
}

// ServiceForComponent builds a ClusterIP Service.
func ServiceForComponent(name, namespace string, port int32, selector map[string]string) *corev1.Service {
	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
		},
		Spec: corev1.ServiceSpec{
			Type:     corev1.ServiceTypeClusterIP,
			Selector: selector,
			Ports: []corev1.ServicePort{
				{
					Name:       "http",
					Port:       port,
					TargetPort: intstr.FromInt32(port),
				},
			},
		},
	}
}

// Int32String returns a string form for status reporting.
func Int32String(v int32) string {
	return strconv.FormatInt(int64(v), 10)
}
