# Kubernetes deployment

Deploy Cogito Review on Kubernetes from scratch using the manifests in this directory.

This is the **Kubernetes mode** installation path. Review agents run as one-shot Jobs reconciled by the Cogito Review Operator. Docker Compose remains the alternative for local or non-Kubernetes environments.

## Container images

| Component | Image |
|-----------|-------|
| API + worker + migrate | `ghcr.io/cogitoforge-ai/cogito-review:latest` |
| Review agent (Jobs) | `ghcr.io/cogitoforge-ai/cogito-review-agent:latest` |
| Operator | `ghcr.io/cogitoforge-ai/cogito-review-operator:latest` |

Pin a release tag instead of `:latest` in production, for example `:0.1.0`.

## Prerequisites

- Kubernetes 1.28+
- `kubectl` configured for your cluster
- **External PostgreSQL** reachable from the cluster
- **External Redis** reachable from the cluster (Celery broker)
- Pull access to `ghcr.io/cogitoforge-ai/*` (public images; use an image pull secret if your cluster requires it)

## Manifest layout

```
deploy/k8s/
├── README.md
├── 01-namespace.yaml          # cogito-review + cogito-review-system
├── 02-operator.yaml           # Operator RBAC + Deployment
├── crd/                       # CustomResourceDefinitions (4 files)
├── 04-secrets.example.yaml    # Template — copy to secrets.yaml
├── 05-configmap.yaml
├── 06-app-rbac.yaml           # API / worker / agent ServiceAccounts
├── 07-policies.yaml           # RuntimePolicy + ScalingPolicy CRs
├── 08-migrate-job.yaml
├── 09-api.yaml                # API Deployment + Service
└── 10-worker.yaml             # Celery worker Deployment
```

## Quick start

### 1. Prepare secrets

```bash
cp deploy/k8s/04-secrets.example.yaml deploy/k8s/secrets.yaml
```

Edit `deploy/k8s/secrets.yaml`:

| Secret | Key | Purpose |
|--------|-----|---------|
| `review-db` | `DATABASE_URL` | PostgreSQL connection string |
| `review-redis` | `REDIS_URL` | Redis URL for Celery |
| `review-callback` | `secret` | HMAC secret for agent callbacks |
| `review-session` | `secret` | Session signing secret |
| `review-encryption` | `key` | Encryption key for stored credentials |

Do not commit `secrets.yaml`.

### 2. Install platform components

Apply manifests in order:

```bash
kubectl apply -f deploy/k8s/01-namespace.yaml
kubectl apply -f deploy/k8s/crd/
kubectl apply -f deploy/k8s/02-operator.yaml

kubectl wait --for=condition=available deployment/cogito-review-operator \
  -n cogito-review-system --timeout=120s
```

### 3. Install application

```bash
kubectl apply -f deploy/k8s/secrets.yaml
kubectl apply -f deploy/k8s/05-configmap.yaml
kubectl apply -f deploy/k8s/06-app-rbac.yaml
kubectl apply -f deploy/k8s/07-policies.yaml
kubectl apply -f deploy/k8s/08-migrate-job.yaml

kubectl wait --for=condition=complete job/cogito-review-migrate \
  -n cogito-review --timeout=300s

kubectl apply -f deploy/k8s/09-api.yaml
kubectl apply -f deploy/k8s/10-worker.yaml
```

### 4. Verify

```bash
kubectl get pods -n cogito-review
kubectl get pods -n cogito-review-system
kubectl get cogitoreviewruntimepolicies,cogitoreviewscalingpolicies -n cogito-review
```

Port-forward the API for a smoke test:

```bash
kubectl port-forward -n cogito-review svc/cogito-review-api 8000:8000
curl -s http://localhost:8000/api/v1/health
```

## How review execution works

1. A webhook creates a review row in PostgreSQL.
2. The Celery worker builds a `CogitoReviewRun` CR (Kubernetes mode).
3. The Operator reconciles the CR and creates a one-shot agent Job using `ghcr.io/cogitoforge-ai/cogito-review-agent`.
4. The agent clones the repository inside the Job Pod, runs the review, and sends callbacks to the API.
5. The Operator updates `CogitoReviewRun` status from Job completion.

The worker does **not** mount the Docker socket. Agent workspace is ephemeral (`emptyDir` at `/workspaces`).

## Customization

### Image tags

Update image references in:

- `05-configmap.yaml` — `COGITO_REVIEW_AGENT_IMAGE`
- `08-migrate-job.yaml`, `09-api.yaml`, `10-worker.yaml` — app image
- `02-operator.yaml` — operator image

### Runtime policy

Edit `07-policies.yaml` to change agent Job resources, TTL, timeout, or the agent ServiceAccount.

### Ingress / public URL

These manifests expose the API as a cluster-internal Service only. Add an Ingress or Gateway API resource pointing to `cogito-review-api.cogito-review.svc:8000`, then set `COGITO_REVIEW_FRONTEND_URL` in the ConfigMap if needed.

### Operator-managed installation (alternative)

Instead of applying `08`–`10` manually, you can use a `CogitoReviewInstallation` CR and let the Operator manage api/worker/migrate. That path is intended for GitOps-style lifecycle control. The manifests in this directory use explicit Deployments for clarity and easier first-time setup.

## Upgrades

1. Update image tags in the manifest files (or your overlay).
2. Re-apply changed manifests:

```bash
kubectl apply -f deploy/k8s/09-api.yaml
kubectl apply -f deploy/k8s/10-worker.yaml
```

3. Run migrations when the app version requires it:

```bash
kubectl delete job cogito-review-migrate -n cogito-review --ignore-not-found
kubectl apply -f deploy/k8s/08-migrate-job.yaml
kubectl wait --for=condition=complete job/cogito-review-migrate -n cogito-review --timeout=300s
```

## CRD sync

CRD YAML under `deploy/k8s/crd/` is copied from `operator/config/crd/bases/`. After changing Go API types, regenerate and copy:

```bash
cd operator && make manifests
cp config/crd/bases/*.yaml ../deploy/k8s/crd/
```

## Uninstall

```bash
kubectl delete -f deploy/k8s/10-worker.yaml --ignore-not-found
kubectl delete -f deploy/k8s/09-api.yaml --ignore-not-found
kubectl delete -f deploy/k8s/08-migrate-job.yaml --ignore-not-found
kubectl delete -f deploy/k8s/07-policies.yaml --ignore-not-found
kubectl delete -f deploy/k8s/06-app-rbac.yaml --ignore-not-found
kubectl delete -f deploy/k8s/05-configmap.yaml --ignore-not-found
kubectl delete -f deploy/k8s/secrets.yaml --ignore-not-found
kubectl delete -f deploy/k8s/02-operator.yaml --ignore-not-found
kubectl delete -f deploy/k8s/crd/ --ignore-not-found
kubectl delete -f deploy/k8s/01-namespace.yaml --ignore-not-found
```

Deleting CRDs removes all custom resources in the cluster.
