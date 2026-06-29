package secrets_test

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"testing"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
	"github.com/cogitoforge-ai/cogito-review/operator/internal/secrets"
)

func TestResolveCredentialBlob(t *testing.T) {
	blob, _ := json.Marshal(map[string]string{
		"COGITO_REVIEW_GITHUB_TOKEN": "ghp_test",
	})
	encoded := base64.StdEncoding.EncodeToString(blob)

	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{Name: "review-test-git", Namespace: "cogito-review"},
		Data: map[string][]byte{
			"credentials": []byte(encoded),
		},
	}
	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(secret).Build()

	out, err := secrets.ResolveCredentialBlob(
		context.Background(),
		c,
		"cogito-review",
		platformv1alpha1.SecretRef{Name: "review-test-git", Key: "credentials"},
	)
	if err != nil {
		t.Fatalf("ResolveCredentialBlob: %v", err)
	}
	if out["COGITO_REVIEW_GITHUB_TOKEN"] != "ghp_test" {
		t.Fatalf("unexpected token: %q", out["COGITO_REVIEW_GITHUB_TOKEN"])
	}
}
