FROM alpine:latest

RUN apk add --no-cache wget tar ca-certificates msr-tools

RUN wget https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz \
    && tar -xf xmrig-6.21.0-linux-static-x64.tar.gz \
    && mv xmrig-6.21.0/xmrig /usr/bin/xmrig \
    && rm -rf xmrig-6.21.0*

COPY run.sh /
RUN chmod a+x /run.sh

ENTRYPOINT ["/bin/sh", "/run.sh"]
