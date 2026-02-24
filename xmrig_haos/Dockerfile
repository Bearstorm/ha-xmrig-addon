FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# HAOS SAFE: bez msr-tools, bez kmod
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# Upstream XMRig verzia je oddelená od add-on version
COPY XMRIG_VERSION /tmp/XMRIG_VERSION

RUN set -eux; \
    VERSION="$(tr -d '\r\n ' < /tmp/XMRIG_VERSION)"; \
    if [[ -z "$VERSION" ]]; then \
      echo "ERROR: XMRIG_VERSION is empty"; \
      exit 1; \
    fi; \
    echo "Downloading upstream XMRig v${VERSION}"; \
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${VERSION}/xmrig-${VERSION}-linux-static-x64.tar.gz"; \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    mv "/tmp/xmrig-${VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    rm -rf /tmp/xmrig* /tmp/XMRIG_VERSION

COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
