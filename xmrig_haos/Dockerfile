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

# 2. Nastavenie verzie priamo v Dockerfile (tu ju jednoducho zmeníš v budúcnosti)
ENV XMRIG_VERSION=6.22.2

# 3. Stiahnutie a inštalácia XMRig
RUN set -eux; \
    echo "Sťahujem XMRig verziu: v${XMRIG_VERSION}"; \
    \
    # Používame linux-x64, ktorý funguje spoľahlivo (vyhýbame sa linux-static)
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/xmrig-${XMRIG_VERSION}-linux-x64.tar.gz"; \
    \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    \
    # Presun binárky do systémovej cesty
    mv "/tmp/xmrig-${XMRIG_VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    \
    # Upratanie dočasných súborov po rozbalení
    rm -rf /tmp/xmrig*

# 4. Skopírovanie spúšťacieho skriptu
# Uisti sa, že v priečinku xmrig_haos máš podpriečinok rootfs a v ňom run.sh
COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
