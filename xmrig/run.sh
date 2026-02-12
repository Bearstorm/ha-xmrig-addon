#!/bin/sh

CONFIG_PATH=/data/options.json

POOL=$(grep -o '"pool": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
PORT=$(grep -o '"port": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
USER=$(grep -o '"user": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
PASS=$(grep -o '"pass": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)

echo "Starting XMRig on: ${POOL}:${PORT} with TLS enabled"

# Vynútené TLS (SSL) spojenie, ktoré port 443 vyžaduje
exec /usr/bin/xmrig --url "${POOL}:${PORT}" --user "$USER" --pass "$PASS" --tls
