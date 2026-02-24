#!/bin/sh

echo "[xmrig-addon] run.sh script started..."

set -u

CONFIG_PATH="/data/options.json"

POOL=$(jq -r '.pool // ""' "$CONFIG_PATH")
PORT=$(jq -r '.port // 0' "$CONFIG_PATH")
WALLET=$(jq -r '.wallet // ""' "$CONFIG_PATH")
WORKER=$(jq -r '.worker // ""' "$CONFIG_PATH")
THREADS=$(jq -r '.threads // 0' "$CONFIG_PATH")
PRIO=$(jq -r '.priority // 0' "$CONFIG_PATH")

POOL_CLEAN=$(echo "$POOL" | sed 's#^[a-zA-Z0-9+.-]*://##')
POOL_HOST="$POOL_CLEAN"
POOL_PORT_FROM_POOL=""

if echo "$POOL_CLEAN" | grep -q ':'; then
  POOL_HOST=$(echo "$POOL_CLEAN" | awk -F: '{print $1}')
  POOL_PORT_FROM_POOL=$(echo "$POOL_CLEAN" | awk -F: '{print $2}')
fi

if [ "$PORT" -gt 0 ] 2>/dev/null; then
  POOL_PORT="$PORT"
elif [ -n "$POOL_PORT_FROM_POOL" ]; then
  POOL_PORT="$POOL_PORT_FROM_POOL"
else
  POOL_PORT="3333"
fi

if [ -z "$POOL_HOST" ] || [ "$POOL_HOST" = "null" ]; then
  echo "[xmrig-addon] ERROR: pool is empty"
  exit 1
fi

if [ -z "$WALLET" ] || [ "$WALLET" = "null" ]; then
  echo "[xmrig-addon] ERROR: wallet is empty"
  exit 1
fi

echo "[xmrig-addon] (HAOS Safe) Starting XMRig on ${POOL_HOST}:${POOL_PORT}"

TLS_ARGS=""
[ "$POOL_PORT" = "443" ] && TLS_ARGS="--tls"

THREAD_ARGS=""
[ "$THREADS" -gt 0 ] && THREAD_ARGS="--threads=${THREADS}"

PRIO_ARGS=""
[ "$PRIO" -gt 0 ] && PRIO_ARGS="--cpu-priority=${PRIO}"

echo "[xmrig-addon] Step 1: Trying FAST mode..."

# OPRAVENÉ: Správne CLI parametre pre XMRig
/usr/bin/xmrig \
  --url "${POOL_HOST}:${POOL_PORT}" \
  --user "$WALLET" \
  --pass "$WORKER" \
  $TLS_ARGS \
  $THREAD_ARGS \
  $PRIO_ARGS \
  --randomx-mode=fast \
  --no-cpu-msr \
  --randomx-no-rdmsr \
  --no-huge-pages

if [ $? -ne 0 ]; then
  echo "[xmrig-addon] FAST mode failed. Switching to LIGHT mode..."
  
  exec /usr/bin/xmrig \
    --url "${POOL_HOST}:${POOL_PORT}" \
    --user "$WALLET" \
    --pass "$WORKER" \
    $TLS_ARGS \
    $THREAD_ARGS \
    $PRIO_ARGS \
    --randomx-mode=light \
    --no-cpu-msr \
    --randomx-no-rdmsr \
    --no-huge-pages
fi
