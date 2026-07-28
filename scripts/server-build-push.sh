#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"

docker_repository=${DOCKERHUB_REPOSITORY:-dockerboi99/he_k8s}
short_sha=$(git rev-parse --short=12 HEAD)
image_tag="sha-$short_sha"
versioned_image="$docker_repository:$image_tag"
latest_image="$docker_repository:latest"

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree must be clean before building a release image." >&2
  exit 1
fi

echo "Building $versioned_image and $latest_image"
docker build --pull \
  -t "$versioned_image" \
  -t "$latest_image" \
  .

echo "Pushing $versioned_image"
docker push "$versioned_image"
echo "Pushing $latest_image"
docker push "$latest_image"

python3 scripts/set_image.py \
  --repository "$docker_repository" \
  --tag latest
python3 scripts/activate_encryptor.py

echo
echo "Images pushed. Review any GitOps change:"
git diff -- deploy/k8s/kustomization.yaml
echo
echo "If a GitOps change is shown:"
echo "  git add deploy/k8s/kustomization.yaml"
echo "  git commit -m 'Deploy $latest_image'"
echo "  git push origin main"
echo
echo "Because latest is mutable, restart the pods after every new push:"
echo "  kubectl -n he-api-dev delete pod -l app=he-add-api"
echo "  kubectl -n he-api-dev delete pod -l app=he-encryptor"
