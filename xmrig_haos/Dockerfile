
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

# 2. Skopírovanie súboru s verziou
# Predpokladáme, že súbor XMRIG_VERSION je v rovnakom priečinku ako Dockerfile
COPY XMRIG_VERSION /tmp/XMRIG_VERSION

# 3. Stiahnutie a inštalácia XMRig
RUN set -eux; \
    # Načítanie verzie a odstránenie bielych znakov (medzery, nové riadky)
    VERSION=$(cat /tmp/XMRIG_VERSION | tr -d '\r\n '); \
    \
    if [[ -z "$VERSION" ]]; then \
      echo "ERROR: XMRIG_VERSION is empty"; \
      exit 1; \
    fi; \
    \
    echo "Sťahujem XMRig verziu: v${VERSION}"; \
    \
    # XMRig vyžaduje v URL 'v' pred číslom verzie, ale v názve archívu nie
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${VERSION}/xmrig-${VERSION}-linux-static-x64.tar.gz"; \
    \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    \
    # Presun binárky do /usr/bin/
    mv "/tmp/xmrig-${VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    \
    # Vyčistenie
    rm -rf /tmp/xmrig* /tmp/XMRIG_VERSION

# 4. Nastavenie spúšťacieho skriptu
COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
