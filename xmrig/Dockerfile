FROM alpine:3.20

RUN set -eux; \
  echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/main" > /etc/apk/repositories; \
  echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/community" >> /etc/apk/repositories; \
  apk add --no-cache wget tar ca-certificates msr-tools jq

RUN wget https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz \
    && tar -xf xmrig-6.21.0-linux-static-x64.tar.gz \
    && mv xmrig-6.21.0/xmrig /usr/bin/xmrig \
    && rm -rf xmrig-6.21.0*

COPY rootfs/run.sh /run.sh
RUN chmod +x /run.sh

ENTRYPOINT ["/bin/sh", "/run.sh"]
