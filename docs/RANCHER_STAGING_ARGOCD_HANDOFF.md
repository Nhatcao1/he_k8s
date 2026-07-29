# Rancher staging Argo CD handoff

The staging server only pulls published code, applies the Argo CD Application,
and checks status. Do not edit, build, commit, or push from the staging server.

## Fill these values

```text
GIT_REPO=<published-repository-url>
BRANCH=main
RANCHER_CONTEXT=<exact-staging-context>
REGISTRY_PROXY=<host>:<port>
REGISTRY_MODE=<transparent-mirror|explicit-address>
EXISTING_IMAGE_TAG=<published-tag>
```

The workload namespace and Argo Application name are both:

```text
datalake-he
```

Argo CD remains in namespace `argocd`.

## Required for the first deploy-only test

- The image referenced by `deploy/k8s/kustomization.yaml` already exists.
- Rancher staging can pull it through the Docker Hub proxy without credentials.
- Argo can read the published Git repository.
- `kubectl` has the correct staging context and permission.

Not required yet:

- GitLab image-build CI;
- a registry pull Secret;
- Kubernetes or Argo credentials in CI;
- an Argo webhook.

## Important Git source rule

`argocd/application.yaml` currently identifies the repository Argo watches.
If GitLab must trigger deployment, its `repoURL` must be the GitLab repository
ending in `.git`. Change and commit that on the development machine before the
server pulls it.

For a private GitLab repository, connect Argo with a read-only GitLab deploy
token scoped only to:

```text
read_repository
```

In the Argo UI, enter:

```text
Settings -> Repositories -> Connect Repo -> HTTPS
Repository URL: https://gitlab.com/<group-or-namespace>/he_k8s.git
Username:       <deploy-token-username>
Password:       <deploy-token-value>
```

Confirm the repository connection reports `Successful` before applying the
Application.

The server user's GitLab login does not authenticate the in-cluster Argo
service. For a public repository, no repository token is required.

## Exact server commands

### 1. Pull published code

```bash
git clone <published-repository-url>
cd he_k8s
git checkout main
git pull --ff-only
git status --short
git rev-parse HEAD
```

Stop unless `git status --short` is empty.

### 2. Select Rancher staging

```bash
kubectl config get-contexts
kubectl config use-context '<exact-staging-context>'
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get crd applications.argoproj.io
kubectl -n argocd get deploy,pod
kubectl auth can-i create applications.argoproj.io -n argocd
```

Stop unless the current context is exactly `RANCHER_CONTEXT`, the nodes belong
to staging, the Argo CRD exists, and the permission check returns `yes`.

### 3. Verify the proxy pull

Choose the form required by Rancher:

```text
transparent mirror -> docker.io/dockerboi99/he_k8s:<tag>
explicit address   -> <host>:<port>/dockerboi99/he_k8s:<tag>
```

Then run:

```bash
kubectl create namespace datalake-he --dry-run=client -o yaml | kubectl apply -f -
kubectl -n datalake-he delete pod registry-pull-check --ignore-not-found
kubectl -n datalake-he run registry-pull-check \
  --image='<correct-image-repository>:<existing-tag>' \
  --restart=Never \
  --command -- python -c "print('registry-pull-ok')"
kubectl -n datalake-he wait pod/registry-pull-check \
  --for=jsonpath='{.status.phase}'=Succeeded \
  --timeout=5m
kubectl -n datalake-he logs registry-pull-check
kubectl -n datalake-he delete pod registry-pull-check
```

For `ImagePullBackOff`, capture:

```bash
kubectl -n datalake-he describe pod registry-pull-check
```

Report the proxy, TLS, path, or tag problem. Do not create registry credentials
for this staging proxy.

### 4. Apply the single Argo Application

Inspect without editing:

```bash
test -f argocd/application.yaml
sed -n '1,80p' argocd/application.yaml
git status --short
kubectl config current-context
```

Confirm the Git URL, branch, `deploy/k8s` path, clean Git status, destination
namespace `datalake-he`, and staging context. Then run exactly:

```bash
kubectl apply -f argocd/application.yaml
kubectl -n argocd get applications.argoproj.io datalake-he -o wide
kubectl -n argocd describe applications.argoproj.io datalake-he
```

Do not run `kubectl apply -k deploy/k8s`. Argo must own the workload resources.

### 5. Verify the CD result

```bash
kubectl -n argocd get applications.argoproj.io datalake-he \
  -o jsonpath='{.status.sync.status}{" "}{.status.health.status}{"\n"}'
kubectl -n datalake-he get deploy,pod,service,job
kubectl -n datalake-he get events --sort-by=.lastTimestamp
kubectl -n datalake-he rollout status deployment/he-add-api --timeout=5m
kubectl -n datalake-he rollout status deployment/he-encryptor --timeout=5m
```

Expected:

```text
Argo sync: Synced
Argo health: Healthy
he-add-api rollout: successful
he-encryptor rollout: successful
he-encrypt-add-smoke-test: successful
```

Argo may delete the successful PostSync Job. If so, use the Application
operation result and events as the evidence.

## Later GitLab automation

The pipeline should test, build and push `sha-<commit>`, update
`deploy/k8s/kustomization.yaml`, and commit that immutable tag to the GitLab
repository Argo watches. CI still needs no Rancher or Argo credentials.
