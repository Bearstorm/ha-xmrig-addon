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

# 2. Skopírovanie súboru s verziou (uisti sa, že súbor XMRIG_VERSION existuje v tvojom repozitári)
# Ak chceš verziu ťahať priamo z config.yaml, zmeň cestu nižšie.
COPY XMRIG_VERSION /tmp/XMRIG_VERSION

# 3. Stiahnutie a inštalácia XMRig
RUN set -eux; \
    # Vyčistenie verzie (odstráni \r, \n, medzery a úvodzovky)
    VERSION=$(cat /tmp/XMRIG_VERSION | tr -d '\r\n" '); \
    \
    if [[ -z "$VERSION" ]]; then \
      echo "ERROR: XMRIG_VERSION is empty"; \
      exit 1; \
    fi; \
    \
    echo "Sťahujem XMRig verziu: v${VERSION}"; \
    \
    # URL na GitHub vyžaduje 'v' pred číslom verzie v ceste, ale archív ho v názve nemá
    wget -O /tmp/xmrig.tar.gz "https://github.com/xmrig/xmrig/releases/download/v${VERSION}/xmrig-${VERSION}-linux-static-x64.tar.gz"; \
    \
    tar -xf /tmp/xmrig.tar.gz -C /tmp; \
    \
    # Presun binárky do systému
    mv "/tmp/xmrig-${VERSION}/xmrig" /usr/bin/xmrig; \
    chmod +x /usr/bin/xmrig; \
    \
    # Upratovanie dočasných súborov
    rm -rf /tmp/xmrig* /tmp/XMRIG_VERSION

# 4. Príprava spúšťacieho skriptu
COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
