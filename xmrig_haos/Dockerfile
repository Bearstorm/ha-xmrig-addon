FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# 1. Inštalácia potrebných nástrojov
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      tar \
      jq; \
    rm -rf /var/lib/apt/lists/*

# 2. Skopírujeme config.yaml do dočasného priečinka, aby sme z neho vytiahli verziu
COPY config.yaml /tmp/addon-config.yaml

# 3. Extrakcia verzie a inštalácia XMRig
RUN set -eux; \
    # Tento príkaz vytiahne "6.21.7" zo súboru config.yaml
    VERSION=$(grep -E '^version:' /tmp/addon-config.yaml | head -n1 | cut -d':' -f2- | tr -d '\r\n" '); \
    \
    if [[ -z "$VERSION" ]]; then \
      echo "ERROR: Verziu sa nepodarilo načítať z config.yaml"; \
      exit 1; \
    fi; \
    \
    echo "Sťahujem XMRig verziu: v${VERSION}"; \
    \
    # Stiahnutie správneho archívu z GitHubu
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${VERSION}/xmrig-${VERSION}-linux-static-x64.tar.gz"; \
    \
    # Rozbalenie a presun binárky
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    mv "/tmp/xmrig-${VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    \
    # Upratovanie
    rm -rf /tmp/xmrig* /tmp/addon-config.yaml

# 4. Spustenie
COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
