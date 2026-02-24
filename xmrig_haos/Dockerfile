FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# 1. Inštalácia potrebných balíkov
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# 2. Nastavenie verzie napevno (najistejšia cesta)
# Použijeme verziu 6.22.2, ktorá je aktuálna a má správne linky
ENV XMRIG_VERSION=6.22.2

# 3. Stiahnutie a inštalácia
RUN set -eux; \
    echo "Sťahujem XMRig verziu: v${XMRIG_VERSION}"; \
    \
    # OPRAVENÁ URL: XMRig zmenil názvoslovie balíkov, linux-static-x64 neexistuje pre každú verziu
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/xmrig-${XMRIG_VERSION}-linux-x64.tar.gz"; \
    \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    \
    # Presun binárky (priečinok po rozbalení nemá v názve '-linux-x64')
    mv "/tmp/xmrig-${XMRIG_VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    \
    # Upratovanie
    rm -rf /tmp/xmrig*

# 4. Spustenie
COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
