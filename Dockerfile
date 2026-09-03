FROM alpine:3.22

RUN apk add --no-cache \
      bash \
      bind-tools \
      busybox-extras \
      curl \
      iproute2 \
      iputils \
      jq \
      netcat-openbsd \
      openssl \
      tcpdump \
      traceroute \
    && addgroup -S -g 10001 toolbox \
    && adduser -S -D -H -u 10001 -G toolbox toolbox

USER 10001:10001

CMD ["sh", "-c", "while true; do sleep 3600; done"]
