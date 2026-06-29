#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLUSTER_NAME="${KIND_CLUSTER_NAME:-cogito-review}"
IMAGE_TAG="${IMAGE_TAG:-local}"
APP_IMAGE="ghcr.io/cogitoforge-ai/cogito-review:${IMAGE_TAG}"
AGENT_IMAGE="ghcr.io/cogitoforge-ai/cogito-review-agent:${IMAGE_TAG}"
OPERATOR_IMAGE="ghcr.io/cogitoforge-ai/cogito-review-operator:${IMAGE_TAG}"

export DOCKER_BUILDKIT=1

echo "==> Building images (tag=${IMAGE_TAG})..."
docker build -f "${ROOT}/Dockerfile" -t "${APP_IMAGE}" "${ROOT}"
docker build -f "${ROOT}/agent/Dockerfile" -t "${AGENT_IMAGE}" "${ROOT}"
docker build -f "${ROOT}/operator/Dockerfile" -t "${OPERATOR_IMAGE}" "${ROOT}/operator"

if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "==> Kind cluster '${CLUSTER_NAME}' already exists"
else
  echo "==> Creating kind cluster '${CLUSTER_NAME}'..."
  kind create cluster --name "${CLUSTER_NAME}"
fi

echo "==> Loading images into kind..."
kind load docker-image "${APP_IMAGE}" --name "${CLUSTER_NAME}"
kind load docker-image "${AGENT_IMAGE}" --name "${CLUSTER_NAME}"
kind load docker-image "${OPERATOR_IMAGE}" --name "${CLUSTER_NAME}"

patch_pull_policy() {
  local file="$1"
  kubectl apply -f "${file}"
  kubectl get deploy,job -n cogito-review -o name 2>/dev/null | while read -r obj; do
    kubectl patch "${obj}" -n cogito-review --type=json \
      -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"Never"}]' 2>/dev/null || true
  done
  kubectl get deploy -n cogito-review-system -o name 2>/dev/null | while read -r obj; do
    kubectl patch "${obj}" -n cogito-review-system --type=json \
      -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"Never"}]' 2>/dev/null || true
  done
}

apply_with_local_images() {
  local src="$1"
  sed \
    -e "s|ghcr.io/cogitoforge-ai/cogito-review:latest|${APP_IMAGE}|g" \
    -e "s|ghcr.io/cogitoforge-ai/cogito-review-agent:latest|${AGENT_IMAGE}|g" \
    -e "s|ghcr.io/cogitoforge-ai/cogito-review-operator:latest|${OPERATOR_IMAGE}|g" \
    -e "s|imagePullPolicy: IfNotPresent|imagePullPolicy: Never|g" \
    "${src}" | kubectl apply -f -
}

echo "==> Applying Kubernetes manifests..."
kubectl apply -f "${ROOT}/deploy/k8s/01-namespace.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/crd/"
apply_with_local_images "${ROOT}/deploy/k8s/02-operator.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/03-infra-postgres-redis.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/secrets.yaml"
apply_with_local_images "${ROOT}/deploy/k8s/05-configmap.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/06-app-rbac.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/07-policies.yaml"

echo "==> Waiting for infra..."
kubectl wait --for=condition=available deployment/postgres -n cogito-review --timeout=180s
kubectl wait --for=condition=available deployment/redis -n cogito-review --timeout=180s
kubectl wait --for=condition=available deployment/cogito-review-operator -n cogito-review-system --timeout=180s

echo "==> Running migrations..."
kubectl delete job cogito-review-migrate -n cogito-review --ignore-not-found
apply_with_local_images "${ROOT}/deploy/k8s/08-migrate-job.yaml"
kubectl wait --for=condition=complete job/cogito-review-migrate -n cogito-review --timeout=300s

apply_with_local_images "${ROOT}/deploy/k8s/09-api.yaml"
apply_with_local_images "${ROOT}/deploy/k8s/10-worker.yaml"

echo "==> Waiting for application..."
kubectl wait --for=condition=available deployment/cogito-review-api -n cogito-review --timeout=180s
kubectl wait --for=condition=available deployment/cogito-review-worker -n cogito-review --timeout=180s

echo ""
echo "==> Pod status"
kubectl get pods -n cogito-review
kubectl get pods -n cogito-review-system

echo ""
echo "==> Access the API:"
echo "  kubectl port-forward -n cogito-review svc/cogito-review-api 8000:8000"
echo "  open http://localhost:8000"
