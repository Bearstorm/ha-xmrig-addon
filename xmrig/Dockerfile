ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Install dependencies
RUN apk add --no-cache wget tar

# Download and setup XMRig
RUN wget https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz \
    && tar -xf xmrig-6.21.0-linux-static-x64.tar.gz \
    && mv xmrig-6.21.0/xmrig /usr/bin/xmrig \
    && rm -rf xmrig-6.21.0*

# Copy execution script
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
