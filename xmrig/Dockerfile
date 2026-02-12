ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Inštalácia potrebných balíkov
RUN apk add --no-cache wget tar

# Stiahnutie XMRig
RUN wget https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz \
    && tar -xf xmrig-6.21.0-linux-static-x64.tar.gz \
    && mv xmrig-6.21.0/xmrig /usr/bin/xmrig \
    && rm -rf xmrig-6.21.0*

# Home Assistant vyžaduje, aby skripty boli v koreňovom adresári
COPY run.sh /
RUN chmod a+x /run.sh

# V roku 2026 je CMD bez ENTRYPOINTu v amd64-base bezpečnejšia voľba pre s6
CMD [ "/run.sh" ]
