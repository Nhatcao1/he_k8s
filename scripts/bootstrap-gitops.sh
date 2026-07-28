#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
kustomization="$repo_dir/deploy/k8s/kustomization.yaml"
application="$repo_dir/argocd/application.yaml"

command -v kubectl >/dev/null 2>&1 || {
  echo "kubectl is required." >&2
  exit 1
}

kubectl get namespace argocd >/dev/null 2>&1 || {
  echo "Argo CD namespace 'argocd' was not found." >&2
  exit 1
}

if grep -q "newTag: bootstrap" "$kustomization"; then
  echo "Refusing to deploy the placeholder image tag." >&2
  exit 1
fi

kubectl apply -f "$application"

echo
echo "Argo CD application:"
kubectl -n argocd get application he-add-api-dev
echo
echo "Watch the rollout with:"
echo "  kubectl -n argocd get application he-add-api-dev -w"
echo "  kubectl -n he-api-dev get pods,service,ingress,jobs -w"
