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

Argo CD itself remains installed in its own `argocd` namespace. The single
Application deploys `deploy/k8s` into `datalake-he` with automated sync,
pruning, and self-healing enabled.

For a transparent Docker Hub mirror, keep:

```text
docker.io/dockerboi99/he_k8s
```

If staging requires an explicit proxy address, update the image repository in
`deploy/k8s/kustomization.yaml` before publishing the Git commit. Do not edit
manifests on the staging server.

## One-time Argo bootstrap

After confirming the Rancher staging context and repository access:

```bash
kubectl apply -f argocd/application.yaml
kubectl -n argocd get applications.argoproj.io datalake-he
```

Do not apply `deploy/k8s` directly. Argo CD owns those resources.

Verify:

```bash
kubectl -n datalake-he get deploy,pod,service,job
kubectl -n datalake-he rollout status deployment/he-add-api --timeout=5m
kubectl -n datalake-he rollout status deployment/he-encryptor --timeout=5m
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
