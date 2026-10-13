
FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# XMRig version and official release SHA-256 checksum
ARG XMRIG_VERSION=6.26.0
ARG XMRIG_SHA256=fc6f8ae5f64e4f17481f7e3be29a1c56949f216a998414188003eae1db20c9e5

# 1. Install required system packages
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# 2. Download and verify the official XMRig binary
RUN set -eux; \
    ARCHIVE="xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz"; \
    URL="https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/${ARCHIVE}"; \
    wget --https-only -O "/tmp/${ARCHIVE}" "${URL}"; \
    echo "${XMRIG_SHA256}  /tmp/${ARCHIVE}" | sha256sum -c -; \
    mkdir -p /tmp/xmrig-extract; \
    tar -xzf "/tmp/${ARCHIVE}" \
      -C /tmp/xmrig-extract \
      --strip-components=1; \
    test -f /tmp/xmrig-extract/xmrig; \
    install -m 0755 /tmp/xmrig-extract/xmrig /usr/bin/xmrig; \
    rm -rf /tmp/xmrig-extract "/tmp/${ARCHIVE}"

# 3. Verify XMRig installation
RUN set -eux; \
    /usr/bin/xmrig --version

# 4. Install the existing startup script
COPY rootfs/run.sh /run.sh

RUN chmod 0755 /run.sh

# 5. Start XMRig using the existing HAOS script
ENTRYPOINT ["/bin/bash", "/run.sh"]
