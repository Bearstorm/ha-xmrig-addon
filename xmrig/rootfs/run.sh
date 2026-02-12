#!/bin/sh
set -eu

CONFIG_PATH="/data/options.json"

POOL="$(jq -r '.pool // ""' "$CONFIG_PATH")"
PORT="$(jq -r '.port // 0' "$CONFIG_PATH")"
WALLET="$(jq -r '.wallet // ""' "$CONFIG_PATH")"
WORKER="$(jq -r '.worker // ""' "$CONFIG_PATH")"
THREADS="$(jq -r '.threads // 0' "$CONFIG_PATH")"
PRIO="$(jq -r '.priority // 0' "$CONFIG_PATH")"

POOL_CLEAN="$(echo "$POOL" | sed 's#^[a-zA-Z0-9+.-]*://##')"

POOL_HOST="$POOL_CLEAN"
POOL_PORT_FROM_POOL=""
if echo "$POOL_CLEAN" | grep -q ':'; then
  POOL_HOST="$(echo "$POOL_CLEAN" | awk -F: '{print $1}')"
  POOL_PORT_FROM_POOL="$(echo "$POOL_CLEAN" | awk -F: '{print $2}')"
fi

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

if [ -z "$WALLET" ]; then
  echo "[xmrig-addon] ERROR: wallet is empty"
  exit 1
fi

echo "[xmrig-addon] Starting XMRig on ${POOL_HOST}:${POOL_PORT}"

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
  --user "$WALLET" \
  --pass "$WORKER" \
  $TLS_ARGS \
  $THREAD_ARGS \
  $PRIO_ARGS \
  --randomx-mode=fast
