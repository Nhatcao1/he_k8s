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
client/service_trial.py          HTTP-only trusted-service workflow client
encryptor/app.py                 trusted encrypt/decrypt session service
tests/                           dependency-free API tests with a fake evaluator
Dockerfile                       Ubuntu 24.04 OpenFHE-Python image
deploy/k8s/                      API, ingress, and encrypted PostSync smoke Job
argocd/application.yaml          Argo CD application for this same repository
scripts/server-build-push.sh     build and push on the Linux server
scripts/set_image.py             update the GitOps image tag
scripts/bootstrap-gitops.sh      create the Argo CD Application
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

The current desired image is:

```text
docker.io/dockerboi99/he_k8s:latest
```

With Argo CD already installed, bootstrap this repository with one command:

```sh
./scripts/bootstrap-gitops.sh
```

Argo CD reads `deploy/k8s`, creates the API, and runs the encrypted PostSync
smoke Job. See [the server runbook](docs/SERVER_RUNBOOK.md) for status commands.

For this testing phase, every workload uses `imagePullPolicy: Always`. The
server build script publishes both `sha-<commit>` and `latest`. Because changing
the contents behind `latest` does not change Git, delete the API and encryptor
pods after each later push so their replacements pull the new image.

## Staged trusted encryptor

The repository also contains a build-ready trusted encryptor service. It
accepts two plaintext vectors, keeps the secret key in a short-lived in-memory
session, and returns an evaluator bundle containing only the context and two
ciphertexts. After the add API returns a result ciphertext, the caller sends
that ciphertext back with the session ID for decryption.

`deploy/k8s/encryptor.yaml` and its HTTP-only smoke Job are intentionally not
active in the Kustomization until an image containing this code is built. The
server build script activates both only after it successfully pushes that new
image. This prevents Argo CD from trying to start the service with the previous
image.

## Current constraint

This first image uses the official `openfhe==1.5.1.0.24.4` Python package. The
final `.24.4` selects the wheel packaged for Ubuntu 24.04; the corresponding
OpenFHE/OpenFHE-Python release is 1.5.1. It does not use HEIR yet. Once
ciphertext addition works through K3s, HEIR-generated functions can be
evaluated as a separate next trial.
