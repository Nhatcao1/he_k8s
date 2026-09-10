FROM alpine:3.22

ARG HADOOP_VERSION=3.4.3
ARG HADOOP_SHA512_AMD64=e25be7e57b4d3c5bfe83895844321a21d6cf7331266d524d8983c27cf484e576c3d79b3b60d590f8cddecf16229d0e232de2491b1b61b362ee7d67072c7290e1
ARG HADOOP_SHA512_ARM64=2f5c1719b801eedecc5bbed0d4c6d61d7c4850dbb5944fb79da24474f694cb5d0f00b07d1b54cade83f6ca492e1697225f47737cc1a4478ca04102062cf314d5

ENV HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/etc/hadoop/conf \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk
ENV PATH="${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin:${PATH}"

RUN apk add --no-cache \
      bash \
      bind-tools \
      busybox-extras \
      curl \
      iproute2 \
      iputils \
      jq \
      kcat \
      krb5 \
      netcat-openbsd \
      nmap \
      openjdk17-jre-headless \
      openssl \
      tcpdump \
      traceroute \
    && case "$(apk --print-arch)" in \
         x86_64) hadoop_archive="hadoop-${HADOOP_VERSION}.tar.gz"; hadoop_sha512="${HADOOP_SHA512_AMD64}" ;; \
         aarch64) hadoop_archive="hadoop-${HADOOP_VERSION}-aarch64.tar.gz"; hadoop_sha512="${HADOOP_SHA512_ARM64}" ;; \
         *) echo "Unsupported architecture: $(apk --print-arch)" >&2; exit 1 ;; \
       esac \
    && curl --fail --location --retry 3 \
         "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/${hadoop_archive}" \
         --output "/tmp/${hadoop_archive}" \
    && echo "${hadoop_sha512}  /tmp/${hadoop_archive}" | sha512sum -c - \
    && mkdir -p "${HADOOP_HOME}" "${HADOOP_CONF_DIR}" \
    && tar -xzf "/tmp/${hadoop_archive}" --strip-components=1 -C "${HADOOP_HOME}" \
    && cp -R "${HADOOP_HOME}/etc/hadoop/." "${HADOOP_CONF_DIR}/" \
    && rm "/tmp/${hadoop_archive}" \
    && addgroup -S -g 10001 toolbox \
    && adduser -S -D -H -u 10001 -G toolbox toolbox

USER 10001:10001

CMD ["sh", "-c", "while true; do sleep 3600; done"]
