# Server build and K3s runbook

The Linux server is the manual build machine. Docker does not need to be
installed on the Mac for this trial.

## Current first deployment

The testing deployment uses:

```text
docker.io/dockerboi99/he_k8s:latest
```

After pulling the repository, the complete GitOps bootstrap is:

```sh
./scripts/bootstrap-gitops.sh
```

The longer build and promotion flow below is for the next image.

## Requirements

- Linux x86-64 server;
- Git and Docker;
- Docker Hub account and repository;
- `kubectl` access to the existing K3s cluster;
- Argo CD already installed in namespace `argocd`.

## 1. Clone

```sh
git clone https://github.com/Nhatcao1/he_k8s.git
cd he_k8s
```

If the repository is private, use the server's existing GitHub credential
method instead of putting a token in the clone URL.

## 2. Log in to Docker Hub

Create a scoped Docker Hub access token, then:

```sh
docker login
```

The default image repository in the scripts is:

```text
dockerboi99/he_k8s
```

No environment variable is needed for the current Docker Hub repository. If it
changes later, override the recorded default with:

```sh
export DOCKERHUB_REPOSITORY=another-name/another-repository
```

## 3. Build and push on the server

The script requires a clean Git worktree. It tags the image with the current
source commit:

```sh
./scripts/server-build-push.sh
```

It performs:

```text
docker build
  -> docker push <repository>:sha-<source-commit>
  -> docker push <repository>:latest
  -> keep deploy/k8s/kustomization.yaml on latest
```

The script stops before committing so the GitOps change remains reviewable.

## 4. Promote the image in the same repository

Review the displayed diff, then run the commands printed by the script:

```sh
git add deploy/k8s/kustomization.yaml
git commit -m "Deploy <repository>:sha-<source-commit>"
git push origin main
```

This is the pretend CI/GitOps split:

- the SHA tag identifies the exact built source;
- `latest` is the convenient mutable testing tag;
- both commits live in `he_k8s.git`.

After every later push to `latest`, restart the two long-running pods so their
replacements pull the new content:

```sh
kubectl -n he-api-dev delete pod -l app=he-add-api
kubectl -n he-api-dev delete pod -l app=he-encryptor
```

## 5. Bootstrap Argo CD once

Only after an actual image tag has been promoted:

```sh
./scripts/bootstrap-gitops.sh
```

Argo CD deploys `deploy/k8s`, waits for the API, and runs the PostSync Job. The
Job creates two encrypted vectors, calls the in-cluster API, decrypts the
returned ciphertext, and exits non-zero if the sum is wrong.

## 6. Check the result

```sh
kubectl -n he-api-dev get pods,service,ingress
kubectl -n he-api-dev logs job/he-add-smoke-test
```

Argo CD may delete a successful hook Job. If it is already gone, check the
Application health and operation result:

```sh
kubectl -n argocd get application he-add-api-dev
```

## 7. Call through Traefik

Map the K3s node address locally:

```text
<K3S_NODE_IP> he-api-dev.k3s.test
```

Then verify:

```sh
curl http://he-api-dev.k3s.test/healthz
curl http://he-api-dev.k3s.test/v1/capabilities
```

To run the encrypted client outside K3s, use the same Docker image or an Ubuntu
24.04 environment with `openfhe==1.5.1.0.24.4`. OpenFHE's Python package
version suffix records the target Ubuntu release.

## Important trial limits

- one API process and one Kubernetes replica;
- no authentication or TLS yet;
- base64 JSON is chosen for simplicity, not efficiency;
- a context is supplied with every request;
- only ciphertext addition is allowed;
- the server never accepts a `secret_key` field;
- `latest` is testing-only; return to immutable SHA tags before production use.
