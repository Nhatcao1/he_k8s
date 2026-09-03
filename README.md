# Network tools GitOps deployment

This repository deploys one long-running network troubleshooting pod through
Argo CD. The image includes `nc`, `curl`, `dig`, `nslookup`, `ping`, `ip`,
`ss`, `telnet`, `traceroute`, `openssl`, `jq`, and `tcpdump`.

## Automatic GitLab build and Argo CD deployment

Pushing this repository to the GitLab default branch runs `.gitlab-ci.yml`:

1. GitLab CI builds the Dockerfile.
2. It pushes `docker.io/dockerboi99/he_k8s:sha-<commit>` to Docker Hub.
3. It writes that immutable image into `deploy/k8s/deployment.yaml` and commits
   the change to GitLab.
4. The existing Argo CD application notices the manifest commit and deploys it.

Configure these masked CI/CD variables in the GitLab project:

- `DOCKERHUB_USERNAME`: the Docker Hub username that owns `dockerboi99/he_k8s`.
- `DOCKERHUB_TOKEN`: a Docker Hub access token with push permission.

The promotion job first tries GitLab's built-in `CI_JOB_TOKEN`. Enable GitLab's
"Allow Git push requests to the repository" setting for job tokens. If that
feature is unavailable, add a masked `GITOPS_PUSH_TOKEN` variable containing a
GitLab project or personal access token with `write_repository` permission.

The GitLab runner must support Docker-in-Docker. No Kubernetes credentials are
stored in GitLab CI: GitLab builds and records the image, while Argo CD performs
the deployment.

For a manual build on another machine:

```bash
docker build -t docker.io/dockerboi99/he_k8s:latest .
docker login
docker push docker.io/dockerboi99/he_k8s:latest
```

## Deploy with Argo CD

Argo CD watches the plain Kubernetes manifests under `deploy/k8s`. No Helm or
Kustomize is used.

`argocd/application.yaml` is only the one-time bootstrap manifest for a cluster
administrator. If an Argo CD application already watches this GitLab repository
and the `deploy/k8s` path, normal deployment requires only a Git push.

GitHub remains a source/backup copy. The bootstrap manifest points Argo CD to
the GitLab repository because that is where image promotion commits are made.

## Use the toolbox

```bash
kubectl -n network-tools exec -it deployment/network-tools -- bash
```

Examples inside the pod:

```bash
nc -vz example.com 443
curl -v https://example.com
dig example.com
ping -c 4 10.0.0.1
traceroute example.com
openssl s_client -connect example.com:443
tcpdump -nn
```
