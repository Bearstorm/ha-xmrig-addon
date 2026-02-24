FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

# Nastavenie premenných, aby sme ich nemuseli hľadať v súboroch
ARG XMRIG_VERSION="6.22.2"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Sťahujeme priamo, bez premenných zo súborov, ktoré by mohli chýbať
RUN wget https://github.com/xmrig/xmrig/releases/download/v6.22.2/xmrig-6.22.2-linux-x64.tar.gz -O /tmp/xmrig.tar.gz \
    && tar -xf /tmp/xmrig.tar.gz -C /tmp \
    && mv /tmp/xmrig-6.22.2/xmrig /usr/bin/xmrig \
    && chmod +x /usr/bin/xmrig \
    && rm -rf /tmp/*

COPY rootfs/run.sh /run.sh
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/bash", "/run.sh"]
