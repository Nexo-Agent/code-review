package secrets

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"

	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	platformv1alpha1 "github.com/cogitoforge-ai/cogito-review/operator/api/v1alpha1"
)

// ResolveSecretKey reads a secret key from the referenced namespace.
func ResolveSecretKey(
	ctx context.Context,
	c client.Client,
	namespace string,
	ref platformv1alpha1.SecretRef,
) (string, error) {
	secretNamespace := ref.Namespace
	if secretNamespace == "" {
		secretNamespace = namespace
	}
	var secret corev1.Secret
	if err := c.Get(ctx, client.ObjectKey{Name: ref.Name, Namespace: secretNamespace}, &secret); err != nil {
		return "", fmt.Errorf("get secret %s/%s: %w", secretNamespace, ref.Name, err)
	}
	raw, ok := secret.Data[ref.Key]
	if !ok {
		return "", fmt.Errorf("secret %s/%s missing key %q", secretNamespace, ref.Name, ref.Key)
	}
	return string(raw), nil
}

// ResolveCredentialBlob reads a JSON credential blob from a secret and returns env vars.
func ResolveCredentialBlob(
	ctx context.Context,
	c client.Client,
	namespace string,
	ref platformv1alpha1.SecretRef,
) (map[string]string, error) {
	raw, err := ResolveSecretKey(ctx, c, namespace, ref)
	if err != nil {
		return nil, err
	}
	decoded := []byte(raw)
	if _, err := base64.StdEncoding.DecodeString(raw); err == nil {
		if b, decErr := base64.StdEncoding.DecodeString(raw); decErr == nil {
			decoded = b
		}
	}
	out := map[string]string{}
	if err := json.Unmarshal(decoded, &out); err != nil {
		return nil, fmt.Errorf("decode credential blob %s/%s: %w", ref.Name, ref.Key, err)
	}
	return out, nil
}
