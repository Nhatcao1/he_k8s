#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"

docker_repository=${DOCKERHUB_REPOSITORY:-dockerboi99/he_k8s}
short_sha=$(git rev-parse --short=12 HEAD)
image_tag="sha-$short_sha"
image="$docker_repository:$image_tag"

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree must be clean before building a release image." >&2
  exit 1
fi

echo "Building $image"
docker build --pull -t "$image" .

echo "Pushing $image"
docker push "$image"

python3 scripts/set_image.py \
  --repository "$docker_repository" \
  --tag "$image_tag"
python3 scripts/activate_encryptor.py

echo
echo "Image pushed. Review the GitOps change:"
git diff -- deploy/k8s/kustomization.yaml
echo
echo "To promote it for Argo CD:"
echo "  git add deploy/k8s/kustomization.yaml"
echo "  git commit -m 'Deploy $image'"
echo "  git push origin main"
