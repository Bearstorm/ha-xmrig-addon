# Development-only installable HAOS beta. Independent of the stable HAOS addon.
# Do not publish to GHCR or deploy to production without separate approval.
# Immutable upstream HA amd64 Bookworm manifest, verified against GHCR package listing (bookworm-2026.08.0).
# Revisit digest explicitly when updating the base image.
FROM ghcr.io/home-assistant/amd64-base-debian:bookworm@sha256:c6a84eec9596b091494a7ba22836090ad56a98a4f73c7b9a9e7590273fc5c5ce
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG XMRIG_VERSION=6.26.0
ARG XMRIG_SHA256=fc6f8ae5f64e4f17481f7e3be29a1c56949f216a998414188003eae1db20c9e5

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates wget tar python3 python3-venv; \
    python3 -m venv /opt/xmrig-venv; \
    /opt/xmrig-venv/bin/pip install --no-cache-dir "paho-mqtt==2.1.0"; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    ARCHIVE="xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz"; \
    URL="https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/${ARCHIVE}"; \
    wget --https-only -O "/tmp/${ARCHIVE}" "${URL}"; \
    echo "${XMRIG_SHA256}  /tmp/${ARCHIVE}" | sha256sum -c -; \
    mkdir -p /tmp/xmrig-extract; \
    tar -xzf "/tmp/${ARCHIVE}" -C /tmp/xmrig-extract --strip-components=1; \
    test -f /tmp/xmrig-extract/xmrig; \
    install -m 0755 /tmp/xmrig-extract/xmrig /usr/bin/xmrig; \
    rm -rf /tmp/xmrig-extract "/tmp/${ARCHIVE}"

COPY rootfs/app/ /opt/xmrig/app/
WORKDIR /opt/xmrig
ENV PYTHONPATH=/opt/xmrig PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# This entrypoint is different from the stable addon only in the beta folder.
ENTRYPOINT ["/opt/xmrig-venv/bin/python", "-m", "app.main"]
