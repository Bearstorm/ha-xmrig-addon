#!/bin/sh

CONFIG_PATH=/data/options.json

# Opravené parsovanie, aby nevznikali dvojité porty
POOL=$(grep -o '"pool": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
PORT=$(grep -o '"port": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
USER=$(grep -o '"user": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
PASS=$(grep -o '"pass": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
THREADS=$(grep -o '"threads": [0-9]*' $CONFIG_PATH | cut -d' ' -f2)
PRIO=$(grep -o '"priority": [0-9]*' $CONFIG_PATH | cut -d' ' -f2)

echo "Starting Bearstorm Miner on ${POOL}:${PORT} with ${THREADS} threads"

# Pridali sme --randomx-mode=fast pre maximálny výkon
if [ "$PORT" = "443" ]; then
    exec /usr/bin/xmrig --url "${POOL}:${PORT}" --user "$USER" --pass "$PASS" --tls --threads="${THREADS}" --cpu-priority="${PRIO}" --randomx-mode=fast
else
    exec /usr/bin/xmrig --url "${POOL}:${PORT}" --user "$USER" --pass "$PASS" --threads="${THREADS}" --cpu-priority="${PRIO}" --randomx-mode=fast
fi
