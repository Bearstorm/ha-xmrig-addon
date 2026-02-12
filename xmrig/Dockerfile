ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Zakázanie s6 overlay, aby sme predišli chybe PID 1
ENV S6_SERVICES_GRACETIME=0
# Home Assistant v roku 2026 vyžaduje toto nastavenie pre manuálne binárky
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2

RUN apk add --no-cache wget tar

RUN wget https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz \
    && tar -xf xmrig-6.21.0-linux-static-x64.tar.gz \
    && mv xmrig-6.21.0/xmrig /usr/bin/xmrig \
    && rm -rf xmrig-6.21.0*

COPY run.sh /
RUN chmod a+x /run.sh

# Toto povie Dockeru, aby spustil skript priamo
ENTRYPOINT ["/run.sh"]
