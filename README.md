# HE ciphertext-add API on K3s

This repository is one small trial:

```text
trusted Python client
  -> encrypt vector A and vector B
  -> POST context + ciphertext A + ciphertext B
  -> API runs OpenFHE EvalAdd(ciphertext A, ciphertext B)
  -> API returns a ciphertext
  -> client decrypts and checks A + B
```

The API never receives the secret key. This is not benchmark code and it is
not yet a production service.

For this trial the same GitHub repository contains:

- the API and trusted client;
- the Dockerfile;
- the K3s manifests;
- the Argo CD Application.

The server acts as the manual CI machine: it clones this repository, builds the
image, pushes it to Docker Hub, and promotes the image tag in this repository.
Argo CD then acts as CD and reconciles the K3s cluster.

The Docker Hub repository for this trial is:

```text
dockerboi99/he_k8s
```

## Files

```text
api/app.py                       HTTP API and OpenFHE EvalAdd evaluator
client/add_client.py             encrypt -> call API -> decrypt smoke client
tests/                           dependency-free API tests with a fake evaluator
Dockerfile                       Ubuntu 24.04 OpenFHE-Python image
deploy/k8s/                      API, ingress, and encrypted PostSync smoke Job
argocd/application.yaml          Argo CD application for this same repository
scripts/server-build-push.sh     build and push on the Linux server
scripts/set_image.py             update the GitOps image tag
docs/SERVER_RUNBOOK.md           exact server commands
```

## API

```text
GET  /healthz
GET  /readyz
GET  /v1/capabilities
POST /v1/add
```

`POST /v1/add` accepts JSON containing three base64-encoded OpenFHE binary
artifacts:

```json
{
  "context": "...",
  "ciphertext_a": "...",
  "ciphertext_b": "..."
}
```

It returns:

```json
{
  "ciphertext": "..."
}
```

Only ciphertext addition is supported. Addition does not require the client to
upload a public key, multiplication key, or rotation key.

## Local tests without OpenFHE

The API contract tests inject a fake evaluator, so they run without Docker or
OpenFHE:

```sh
python3 -m unittest discover -s tests -v
```

The actual cryptographic smoke test runs in the Linux image:

```sh
python3 -m client.add_client \
  --url http://127.0.0.1:8080/v1/add
```

## Server deployment

Follow [the server runbook](docs/SERVER_RUNBOOK.md). Do not bootstrap Argo CD
until the server has built an actual image and promoted its tag.

## Current constraint

This first image uses the official `openfhe==1.5.1.0` Python package on Ubuntu
24.04. It does not use HEIR yet. Once ciphertext addition works through K3s,
HEIR-generated functions can be evaluated as a separate next trial.
