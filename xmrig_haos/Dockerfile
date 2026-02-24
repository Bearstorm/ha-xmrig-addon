FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# 1. Inštalácia závislostí
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# 2. Nastavenie verzie priamo v Dockerfile (aby sme nemuseli COPY config.yaml)
ENV XMRIG_VERSION=6.22.2

# 3. Stiahnutie a inštalácia
RUN set -eux; \
    echo "Sťahujem XMRig v${XMRIG_VERSION}"; \
    \
    # Používame linux-x64, ktorý je dostupný pre všetky novšie verzie
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/xmrig-${XMRIG_VERSION}-linux-x64.tar.gz"; \
    \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    \
    # Priečinok po rozbalení sa volá xmrig-6.22.2
    mv "/tmp/xmrig-${XMRIG_VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    \
    rm -rf /tmp/xmrig*

# 4. Spustenie - uisti sa, že run.sh je v xmrig_haos/rootfs/run.sh
COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
