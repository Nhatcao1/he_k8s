# Network tools GitOps deployment

This repository deploys one long-running network troubleshooting pod through
Argo CD. The image includes `nc`, `curl`, `dig`, `nslookup`, `ping`, `ip`,
`ss`, `telnet`, `traceroute`, `openssl`, `jq`, and `tcpdump`.

## Build and publish the image

```bash
docker build -t docker.io/dockerboi99/he_k8s:latest .
docker login
docker push docker.io/dockerboi99/he_k8s:latest
```

## Deploy with Argo CD

Argo CD watches the plain Kubernetes manifests under `deploy/k8s`. No Helm or
Kustomize is used.

```bash
kubectl apply -f argocd/application.yaml
kubectl -n network-tools rollout status deployment/network-tools
```

If Argo CD runs in a namespace other than `argocd`, change
`metadata.namespace` in `argocd/application.yaml` before applying it.

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
```
