
FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# HAOS safe: minimum packages
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# Upstream XMRig version (NOT addon version)
COPY XMRIG_VERSION /tmp/XMRIG_VERSION

RUN set -eux; \
    XMRIG_VERSION="$(tr -d '\r\n ' < /tmp/XMRIG_VERSION)"; \
    if [[ -z "$XMRIG_VERSION" ]]; then \
      echo "ERROR: XMRIG_VERSION is empty"; \
      echo "--- /tmp/XMRIG_VERSION ---"; \
      cat /tmp/XMRIG_VERSION || true; \
      exit 1; \
    fi; \
    echo "Using upstream XMRig version: $XMRIG_VERSION"; \
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz"; \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    mv "/tmp/xmrig-${XMRIG_VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    rm -rf /tmp/xmrig* /tmp/XMRIG_VERSION

COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# HAOS safe: minimum packages
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# Upstream XMRig version (NOT addon version)
COPY XMRIG_VERSION /tmp/XMRIG_VERSION

RUN set -eux; \
    XMRIG_VERSION="$(tr -d '\r\n ' < /tmp/XMRIG_VERSION)"; \
    if [[ -z "$XMRIG_VERSION" ]]; then \
      echo "ERROR: XMRIG_VERSION is empty"; \
      echo "--- /tmp/XMRIG_VERSION ---"; \
      cat /tmp/XMRIG_VERSION || true; \
      exit 1; \
    fi; \
    echo "Using upstream XMRig version: $XMRIG_VERSION"; \
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz"; \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    mv "/tmp/xmrig-${XMRIG_VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    rm -rf /tmp/xmrig* /tmp/XMRIG_VERSION

COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
