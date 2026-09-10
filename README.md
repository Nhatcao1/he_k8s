# Network tools GitOps deployment

This repository deploys one network troubleshooting pod through Argo CD using a
standard Kubernetes Deployment. The image includes `nc`, `curl`, `dig`,
`nslookup`, `ping`, `ip`, `ss`, `telnet`, `traceroute`, `nmap`, `kcat`,
`hdfs dfs`, `kinit`, `openssl`, `jq`, and `tcpdump`. The container runs as
non-root UID/GID `10001` for restricted Kubernetes environments. The pod
receives only the `NET_RAW` Linux capability needed by `ping`, TCP traceroute,
and raw-socket diagnostics.

## Automatic GitLab build and Argo CD deployment

Pushing this repository to the GitLab default branch runs `.gitlab-ci.yml`:

1. GitLab CI builds the Dockerfile.
2. It pushes `docker.io/dockerboi99/he_k8s:sha-<commit>` and `latest` to Docker
   Hub.
3. It writes that immutable image into `deploy/k8s/deployment.yaml` and commits
   the change to GitLab.
4. The existing Argo CD application notices the manifest commit and deploys it.

## Select staging or production

Environment settings are separate:

```text
deploy.env                 default environment selector
environments/stag.env      staging image and manifest settings
environments/prod.env      production image and manifest settings
deploy/k8s/deployment.yaml  staging plain YAML
deploy/prod/deployment.yaml production plain YAML
```

Staging is the default. Change this line in `deploy.env` and push when production
should receive the next build:

```dotenv
DEFAULT_DEPLOY_ENV=prod
```

Alternatively, start a GitLab pipeline with `DEPLOY_ENV=prod`; that variable
overrides the default without changing the file. Accepted values are only
`stag` and `prod`.

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

The two files under `argocd/` are one-time bootstrap manifests for a cluster
administrator. After the staging and production Argo applications exist, normal
deployment requires only a Git push or a GitLab pipeline run.

The supplied applications use separate namespaces in the same Kubernetes
cluster. A cluster administrator can change `destination.server` in either Argo
application if staging and production are separate clusters.

GitHub remains a source/backup copy. The bootstrap manifest points Argo CD to
the GitLab repository because that is where image promotion commits are made.

## Use the toolbox

List the deployed pod:

```bash
kubectl -n network-tools-stag get pods -l app=network-tools -o wide
```

Open the pod:

```bash
kubectl -n network-tools-stag exec -it <pod-name> -- bash
```

Inside the pod, `NODE_NAME` identifies the Kubernetes node selected by the
scheduler.

Examples inside the pod:

```bash
nc -vz example.com 443
nmap -sT -Pn -p 443 example.com
kcat -b 10.211.144.162:8464 -L -m 5
curl -v https://example.com
dig example.com
ping -c 4 10.0.0.1
traceroute example.com
openssl s_client -connect example.com:443
tcpdump -nn
```

## Configure the HDFS client

The image includes the Hadoop 3.4.3 client and Java 17. Hadoop configuration is
read from `HADOOP_CONF_DIR=/etc/hadoop/conf`. The safest setup is to request the
cluster's existing `core-site.xml` and `hdfs-site.xml` from the HDFS
administrator and mount both files into that directory. This matters especially
for HA nameservices, Kerberos, custom RPC ports, and vendor-specific settings.

For a simple, non-HA and non-Kerberos HDFS cluster, the minimum
`core-site.xml` is:

```xml
<?xml version="1.0"?>
<configuration>
  <property>
    <name>fs.defaultFS</name>
    <value>hdfs://namenode.example.internal:8020</value>
  </property>
</configuration>
```

Then run:

```bash
hdfs getconf -confKey fs.defaultFS
hdfs dfs -ls /
hdfs dfs -put /tmp/test.txt /tmp/test.txt
hdfs dfs -cat /tmp/test.txt
```

For an HA cluster, do not replace the logical nameservice with a single
NameNode IP. Its `hdfs-site.xml` normally defines `dfs.nameservices`, the HA
NameNode IDs and RPC addresses, and
`dfs.client.failover.proxy.provider.<nameservice>`. Copy the cluster-provided
files so failover and address discovery work correctly.

For a Kerberos-secured cluster, also mount the organization's `krb5.conf` at
`/etc/krb5.conf` and a keytab as a Kubernetes Secret, then authenticate before
using HDFS:

```bash
kinit -kt /etc/security/keytabs/client.keytab user@EXAMPLE.COM
klist
hdfs dfs -ls /
```

Do not commit `krb5.conf`, keytabs, passwords, or Hadoop credentials to this
repository. HDFS clients contact the NameNode for metadata and then connect
directly to DataNodes for file blocks. Network policy/firewalls must therefore
allow DNS plus the NameNode RPC endpoint and the DataNode transfer endpoints;
opening only port `8020` is usually insufficient for file reads and writes.
