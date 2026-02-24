FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq \
      msr-tools \
      kmod; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    wget -O /tmp/xmrig.tar.gz https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz; \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    mv /tmp/xmrig-6.21.0/xmrig /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    rm -rf /tmp/xmrig* /tmp/xmrig.tar.gz

COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
