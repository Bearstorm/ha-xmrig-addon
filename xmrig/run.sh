#!/bin/sh

CONFIG_PATH=/data/options.json

# Čisté načítanie hodnôt bez duplikátov
POOL=$(grep -o '"pool": "[^"]*' $CONFIG_PATH | cut -d'"' -f4 | sed 's/.*:\/\///;s/:.*//')
PORT=$(grep -o '"port": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
USER=$(grep -o '"user": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
PASS=$(grep -o '"pass": "[^"]*' $CONFIG_PATH | cut -d'"' -f4)
THREADS=$(grep -o '"threads": [0-9]*' $CONFIG_PATH | cut -d' ' -f2)
PRIO=$(grep -o '"priority": [0-9]*' $CONFIG_PATH | cut -d' ' -f2)

echo "Starting Bearstorm Miner on ${POOL} at port ${PORT}"

# Kľúč k MSR: Musíme vytvoriť uzly vnútri kontajnera, ak chýbajú
if [ ! -c /dev/cpu/0/msr ]; then
  mkdir -p /dev/cpu/0
  mknod /dev/cpu/0/msr c 202 0 2>/dev/null
fi

# Spustenie
if [ "$PORT" = "443" ]; then
    exec /usr/bin/xmrig \
      --url "${POOL}:${PORT}" \
      --user "$USER" \
      --pass "$PASS" \
      --tls \
      --threads="${THREADS}" \
      --cpu-priority="${PRIO}" \
      --randomx-mode=fast
else
    exec /usr/bin/xmrig \
      --url "${POOL}:${PORT}" \
      --user "$USER" \
      --pass "$PASS" \
      --threads="${THREADS}" \
      --cpu-priority="${PRIO}" \
      --randomx-mode=fast
fi
