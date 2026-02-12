#!/bin/sh

CONFIG_PATH=/data/options.json

POOL=$(grep -o '"pool": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
USER=$(grep -o '"user": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
PASS=$(grep -o '"pass": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)

echo "Starting XMRig on pool: $POOL"

exec /usr/bin/xmrig --url "$POOL" --user "$USER" --pass "$PASS"
