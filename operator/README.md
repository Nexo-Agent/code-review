# Cogito Review Kubernetes Operator

Go operator (Kubebuilder) for Kubernetes-native Cogito Review installation and review execution.

## Prerequisites

- Go 1.23+
- kubectl
- [Kubebuilder](https://kubebuilder.io/) (installed to `../.tools/bin/kubebuilder` in this repo)

## Development

```bash
# Install kubebuilder locally (once)
mkdir -p ../.tools/bin
curl -L -o ../.tools/bin/kubebuilder \
  "https://go.kubebuilder.io/dl/latest/$(go env GOOS)/$(go env GOARCH)"
chmod +x ../.tools/bin/kubebuilder

make generate manifests build test
```

## Install CRDs and operator

```bash
kubectl apply -f config/crd/bases/
kubectl apply -k config/default/
```

## CRDs

| Resource | Purpose |
|----------|---------|
| `CogitoReviewRun` | Execution intent for one review (creates agent Job) |
| `CogitoReviewInstallation` | Root installation (api, worker, migrate, services) |
| `CogitoReviewRuntimePolicy` | Agent Job policy (resources, TTL, service account) |
| `CogitoReviewScalingPolicy` | Replica and concurrency settings |

API group: `platform.cogito.review/v1alpha1`

## Deployment examples

See [deploy/k8s/README.md](../deploy/k8s/README.md) for a full Kubernetes installation using the manifests in `deploy/k8s/`.

## Schema contracts

Cross-language contracts live in `shared/coreview_shared/schemas/`:

- `review-execution-request-v1.schema.json`
- `kubernetes-execution-spec-v1.schema.json`
- `cogito-review-run-v1.schema.json`

Run compatibility validation:

```bash
bash ../scripts/validate-k8s-contracts.sh
```
