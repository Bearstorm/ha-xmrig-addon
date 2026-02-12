#!/bin/sh
set -eu

CONFIG_PATH="/data/options.json"

POOL="$(jq -r '.pool // ""' "$CONFIG_PATH")"
PORT="$(jq -r '.port // 0' "$CONFIG_PATH")"
USER="$(jq -r '.user // ""' "$CONFIG_PATH")"
PASS="$(jq -r '.pass // ""' "$CONFIG_PATH")"
THREADS="$(jq -r '.threads // 0' "$CONFIG_PATH")"
PRIO="$(jq -r '.priority // 0' "$CONFIG_PATH")"

# Odstráň scheme ak niekto zadá napr. stratum+ssl://...
POOL_CLEAN="$(echo "$POOL" | sed 's#^[a-zA-Z0-9+.-]*://##')"

# Ak je pool host:port, rozdeľ
POOL_HOST="$POOL_CLEAN"
POOL_PORT_FROM_POOL=""
if echo "$POOL_CLEAN" | grep -q ':'; then
  POOL_HOST="$(echo "$POOL_CLEAN" | awk -F: '{print $1}')"
  POOL_PORT_FROM_POOL="$(echo "$POOL_CLEAN" | awk -F: '{print $2}')"
fi

# Port: preferuj .port, inak z pool, inak default 3333
if [ "$PORT" -gt 0 ] 2>/dev/null; then
  POOL_PORT="$PORT"
elif [ -n "$POOL_PORT_FROM_POOL" ]; then
  POOL_PORT="$POOL_PORT_FROM_POOL"
else
  POOL_PORT="3333"
fi

if [ -z "$POOL_HOST" ]; then
  echo "[xmrig-addon] ERROR: pool is empty"
  exit 1
fi

if [ -z "$USER" ]; then
  echo "[xmrig-addon] ERROR: user is empty"
  exit 1
fi

echo "[xmrig-addon] Starting XMRig on ${POOL_HOST}:${POOL_PORT}"

# MSR: nič nevytvárať cez mknod (to je zle). Len informácia.
if [ -c /dev/cpu/0/msr ]; then
  echo "[xmrig-addon] MSR device present: /dev/cpu/0/msr"
else
  echo "[xmrig-addon] WARNING: MSR device missing: /dev/cpu/0/msr"
fi

TLS_ARGS=""
if [ "$POOL_PORT" = "443" ]; then
  TLS_ARGS="--tls"
fi

THREAD_ARGS=""
if [ "$THREADS" -gt 0 ] 2>/dev/null; then
  THREAD_ARGS="--threads=${THREADS}"
fi

PRIO_ARGS=""
if [ "$PRIO" -gt 0 ] 2>/dev/null; then
  PRIO_ARGS="--cpu-priority=${PRIO}"
fi

exec /usr/bin/xmrig \
  --url "${POOL_HOST}:${POOL_PORT}" \
  --user "$USER" \
  --pass "$PASS" \
  $TLS_ARGS \
  $THREAD_ARGS \
  $PRIO_ARGS \
  --randomx-mode=fast

