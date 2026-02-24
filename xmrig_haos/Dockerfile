FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Potrebujeme len základ (HAOS safe): bez msr-tools, bez kmod
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# Prekopíruj config.yaml kvôli verzii (build-time)
COPY config.yaml /tmp/addon-config.yaml

# Stiahni XMRig verziu presne podľa config.yaml (napr. 6.21.7)
RUN set -eux; \
    VERSION="$(grep -E '^version:' /tmp/addon-config.yaml | head -n1 | cut -d':' -f2- | tr -d '\r\n' | tr -d ' "')"; \
    if [[ -z "$VERSION" ]]; then \
      echo "ERROR: VERSION is empty from config.yaml"; \
      echo "--- config.yaml ---"; \
      cat /tmp/addon-config.yaml; \
      exit 1; \
    fi; \
    echo "Using XMRig VERSION=$VERSION from xmrig_haos/config.yaml"; \
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${VERSION}/xmrig-${VERSION}-linux-static-x64.tar.gz"; \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    mv "/tmp/xmrig-${VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    rm -rf /tmp/xmrig* /tmp/addon-config.yaml

COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
