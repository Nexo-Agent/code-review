package job_test

import (
	"testing"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
	jobbuilder "github.com/cogitoforge-ai/cogito-review/operator/internal/job"
)

func TestBuildAgentJob(t *testing.T) {
	run := &platformv1alpha1.CogitoReviewRun{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "review-550e8400-e29b-41d4-a716-446655440000",
			Namespace: "cogito-review",
		},
		Spec: platformv1alpha1.CogitoReviewRunSpec{
			Review: platformv1alpha1.CogitoReviewRunReview{
				ReviewID:     "550e8400-e29b-41d4-a716-446655440000",
				RepoFullName: "acme/service-a",
				PRNumber:     42,
				HeadSHA:      "abc123",
			},
			Execution: platformv1alpha1.CogitoReviewRunExecution{
				Kind: "kubernetes",
				Spec: platformv1alpha1.KubernetesExecutionInnerSpec{
					AgentImage: "ghcr.io/cogitoforge-ai/cogito-review-agent:latest",
					Callback: platformv1alpha1.CallbackSpec{
						Mode: "internal-service",
						URL:  "http://cogito-review-api/api/v1/agent/review-events",
						SecretRef: platformv1alpha1.SecretRef{
							Name: "review-callback",
							Key:  "secret",
						},
					},
					Workspace: platformv1alpha1.WorkspaceSpec{
						Strategy: "ephemeral-clone",
						RootPath: "/workspaces",
					},
					Credentials: platformv1alpha1.CredentialRefs{
						GitCredentialRef: platformv1alpha1.SecretRef{Name: "git", Key: "credentials"},
						LLMCredentialRef: platformv1alpha1.SecretRef{Name: "llm", Key: "credentials"},
					},
					Environment: map[string]string{
						"COGITO_REVIEW_GIT_PROVIDER": "github",
					},
				},
			},
		},
	}

	job := jobbuilder.BuildAgentJob(run, map[string]string{
		"COGITO_REVIEW_CALLBACK_SECRET": "secret",
	}, jobbuilder.DefaultRuntimePolicy("cogito-review"))

	if job.Spec.Template.Spec.Containers[0].Image != run.Spec.Execution.Spec.AgentImage {
		t.Fatalf("unexpected image: %s", job.Spec.Template.Spec.Containers[0].Image)
	}
	if len(job.Spec.Template.Spec.Volumes) != 1 {
		t.Fatalf("expected one workspace volume")
	}
	if job.Spec.Template.Spec.Volumes[0].EmptyDir == nil {
		t.Fatalf("expected emptyDir workspace volume")
	}
}
