# Minimal HE add CD trial

This repository is a small continuous-delivery trial for Rancher-managed
Kubernetes staging. It intentionally deploys only two services and one
end-to-end test:

```text
he-encryptor
  -> encrypt two plaintext vectors and retain the secret key in memory
he-add-api
  -> evaluate OpenFHE ciphertext addition without receiving the secret key
he-encrypt-add-smoke-test
  -> encrypt -> add -> decrypt -> verify the numerical sum
```

It is trial code, not a production cryptography service.

## Components

```text
api/app.py                         ciphertext-add HTTP evaluator
encryptor/app.py                   trusted encrypt/decrypt session service
client/service_trial.py            HTTP-only end-to-end verification client
deploy/k8s/he-add-api.yaml         add Deployment and Service
deploy/k8s/he-encryptor.yaml       encryptor Deployment and Service
deploy/k8s/e2e-smoke-test.yaml     Argo CD PostSync verification Job
deploy/k8s/kustomization.yaml      namespace and image selection
argocd/application.yaml            single Argo CD Application
docs/RANCHER_STAGING_ARGOCD_HANDOFF.md
```

There is no gateway, external Ingress, client SDK, or direct server build in
this CD trial. The smoke test runs inside the cluster.

## End-to-end operation

`client.service_trial` performs:

1. `POST /v1/encrypt-pair` to `he-encryptor`;
2. `POST /v1/add` to `he-add-api`;
3. `POST /v1/sessions/{id}/decrypt` to `he-encryptor`;
4. comparison of the decrypted values with `left + right`.

The Job exits non-zero if an HTTP request fails, the response shape is wrong,
or the CKKS error exceeds the configured tolerance. That makes a failed
cryptographic path fail the Argo PostSync operation.

## Local dependency-free tests

The unit and HTTP contract tests use fake evaluators and do not require
OpenFHE:

```bash
python3 -m unittest discover -s tests -v
```

The real OpenFHE test runs inside the published Linux image and Kubernetes Job.

## Kubernetes layout

The workload namespace is:

```text
datalake-he
```

The Application resource and workloads use namespace `datalake-he`. The
cluster's Argo CD installation may remain in a different control-plane
namespace. The `datalake` AppProject and Argo CD installation must allow
Applications from `datalake-he`.

The repository does not create or manage that namespace. `datalake-he` must
already exist and be administered by the staging platform team.

The trial pulls through the staging registry proxy:

```text
hub.vtcc.vn:8989/dockerboi99/he_k8s:latest
```

Kustomize replaces the base Docker Hub image name with that explicit registry
address. Update `newName` and `newTag` in `deploy/k8s/kustomization.yaml`
before publishing a changed image. Do not edit workload manifests on staging.

## One-time Argo bootstrap

After confirming the Rancher staging context and repository access:

```bash
kubectl --insecure-skip-tls-verify=true get namespace datalake-he
kubectl --insecure-skip-tls-verify=true apply -f argocd/application.yaml
kubectl --insecure-skip-tls-verify=true -n datalake-he \
  get applications.argoproj.io datalake-he
```

Do not apply `deploy/k8s` directly. Argo CD owns those resources.

Verify:

```bash
kubectl --insecure-skip-tls-verify=true -n datalake-he \
  get deploy,pod,service,job
kubectl --insecure-skip-tls-verify=true -n datalake-he \
  rollout status deployment/he-add-api --timeout=5m
kubectl --insecure-skip-tls-verify=true -n datalake-he \
  rollout status deployment/he-encryptor --timeout=5m
```

Argo may delete a successful PostSync Job according to its hook policy. Check
the Argo operation result if the completed Job is already gone.

## Image promotion

GitHub is currently the source-transfer path, not the image builder. The first
CD trial therefore uses an image that has already been published and records
that tag in `deploy/k8s/kustomization.yaml`.

When GitLab CI is added, it should test, build and push an immutable
`sha-<commit>` image, then commit that tag into the Git repository Argo watches.
GitLab CI does not need Kubernetes or Argo credentials.

## Trial limits

- one replica per service;
- no external Ingress, authentication, or TLS;
- secret keys and sessions exist in encryptor memory;
- sessions disappear when the encryptor restarts;
- only ciphertext addition is evaluated;
- CKKS results are approximate;
- use immutable image tags for repeatable deployment and rollback.
