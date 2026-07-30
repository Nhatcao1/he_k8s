# Rancher staging Argo CD handoff

The staging server only pulls published code, creates the Argo CD Application,
and checks status. Do not edit, build, commit, or push from staging.

## Values already configured in Git

```text
GIT_REPO=http://source.cyberspace.vn/nhatcm1/he_k8s.git
BRANCH=main
ARGO_PROJECT=datalake
APPLICATION_NAMESPACE=datalake-he
WORKLOAD_NAMESPACE=datalake-he
MANIFEST_PATH=deploy/k8s
REGISTRY_PROXY=hub.vtcc.vn:8989
REGISTRY_MODE=explicit-address
EXISTING_IMAGE=hub.vtcc.vn:8989/dockerboi99/he_k8s:latest
```

Only this value must be selected on the staging server:

```text
RANCHER_CONTEXT=<exact-staging-context>
```

Do not change `MANIFEST_PATH` to `argocd`. The `argocd` directory contains the
bootstrap Application; the Deployments, Services, and smoke-test Job are under
`deploy/k8s`.

## What applying the Application does

`kubectl apply -f argocd/application.yaml` creates or updates one Kubernetes
custom resource. Argo CD then sees that resource and, because automated sync is
enabled, reads the Git repository, renders `deploy/k8s`, and creates the HE
Deployments, Services, Pods, and PostSync test Job.

The chain only proceeds when all of these are true:

- Argo CD can read the Git repository;
- AppProject `datalake` permits that repository and destination;
- Argo CD accepts Applications from namespace `datalake-he`;
- AppProject `datalake.spec.sourceNamespaces` includes `datalake-he`;
- the staging cluster can pull the configured image.

The Application resource is in `datalake-he`; the Argo CD controllers can be
installed in another namespace. No Argo username or password is stored in this
repository or passed to `kubectl`. Argo UI credentials are only for logging
into the UI/CLI. Repository credentials, if required, are configured once in
Argo CD as a read-only repository connection.

## Exact staging-server commands

Every command below skips kube-apiserver TLS verification because that is
required by this staging setup.

### 1. Pull the published repository

```bash
git clone http://source.cyberspace.vn/nhatcm1/he_k8s.git
cd he_k8s
git checkout main
git pull --ff-only
git status --short
git rev-parse HEAD
```

Stop unless `git status --short` is empty.

### 2. Select and verify Rancher staging

```bash
kubectl --insecure-skip-tls-verify=true config get-contexts
kubectl --insecure-skip-tls-verify=true config use-context '<exact-staging-context>'
kubectl --insecure-skip-tls-verify=true config current-context
kubectl --insecure-skip-tls-verify=true cluster-info
kubectl --insecure-skip-tls-verify=true get nodes -o wide
kubectl --insecure-skip-tls-verify=true get crd applications.argoproj.io
kubectl --insecure-skip-tls-verify=true get appprojects.argoproj.io -A
kubectl --insecure-skip-tls-verify=true auth can-i create \
  applications.argoproj.io -n datalake-he
```

Stop unless the current context is the intended staging context, the nodes are
staging nodes, the Argo Application CRD exists, AppProject `datalake` exists,
and the permission check returns `yes`.

Because this Application is outside the Argo CD control-plane namespace, the
server's Argo administrator must also confirm:

```text
argocd-application-controller --application-namespaces includes datalake-he
argocd-server                 --application-namespaces includes datalake-he
AppProject datalake           spec.sourceNamespaces includes datalake-he
```

If those settings are not enabled, do not move the Application silently.
Ask the Argo administrator which control-plane namespace must hold it.

### 3. Verify the exact image can be pulled

```bash
kubectl --insecure-skip-tls-verify=true create namespace datalake-he \
  --dry-run=client -o yaml |
  kubectl --insecure-skip-tls-verify=true apply -f -

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  delete pod registry-pull-check --ignore-not-found

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  run registry-pull-check \
  --image='hub.vtcc.vn:8989/dockerboi99/he_k8s:latest' \
  --restart=Never \
  --command -- python -c "print('registry-pull-ok')"

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  wait pod/registry-pull-check \
  --for=jsonpath='{.status.phase}'=Succeeded \
  --timeout=5m

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  logs registry-pull-check

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  delete pod registry-pull-check
```

For `ImagePullBackOff`, capture:

```bash
kubectl --insecure-skip-tls-verify=true -n datalake-he \
  describe pod registry-pull-check
```

Do not create registry credentials for this credential-free staging proxy.

### 4. Inspect and apply the Application

```bash
test -f argocd/application.yaml
sed -n '1,80p' argocd/application.yaml
git status --short
kubectl --insecure-skip-tls-verify=true config current-context
```

Confirm these exact fields:

```text
repoURL:        http://source.cyberspace.vn/nhatcm1/he_k8s.git
targetRevision: main
path:           deploy/k8s
project:        datalake
metadata ns:    datalake-he
destination ns: datalake-he
```

Then apply:

```bash
kubectl --insecure-skip-tls-verify=true apply \
  -f argocd/application.yaml

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  get applications.argoproj.io datalake-he -o wide

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  describe applications.argoproj.io datalake-he
```

Do not run `kubectl apply -k deploy/k8s`. Argo CD owns those resources.

### 5. Verify Argo created the workloads

```bash
kubectl --insecure-skip-tls-verify=true -n datalake-he \
  get applications.argoproj.io datalake-he \
  -o jsonpath='{.status.sync.status}{" "}{.status.health.status}{"\n"}'

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  get deploy,pod,service,job

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  get events --sort-by=.lastTimestamp

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  rollout status deployment/he-add-api --timeout=5m

kubectl --insecure-skip-tls-verify=true -n datalake-he \
  rollout status deployment/he-encryptor --timeout=5m
```

Expected:

```text
Argo sync: Synced
Argo health: Healthy
he-add-api rollout: successful
he-encryptor rollout: successful
he-encrypt-add-smoke-test: successful
```

Argo may delete a successful PostSync Job according to its hook policy. If it
is already gone, use the Application operation result and events as evidence.

## Later GitLab automation

No special GitLab build pipeline is needed for this first deploy-only test.
Argo polls Git and automatically syncs commits that change `deploy/k8s`.

Later, CI should test, build and push an immutable `sha-<commit>` image, update
`newTag` in `deploy/k8s/kustomization.yaml`, and commit that tag to this Git
repository. CI still needs no Rancher, Kubernetes, or Argo credentials.
