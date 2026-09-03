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
      traceroute

CMD ["sh", "-c", "while true; do sleep 3600; done"]
