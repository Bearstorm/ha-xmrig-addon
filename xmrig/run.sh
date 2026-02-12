#!/bin/sh
set -eu

CONFIG_PATH="/data/options.json"

# Bezpečné čítanie JSON cez jq (žiadne grep/regex na JSON)
POOL="$(jq -r '.pool // ""' "$CONFIG_PATH")"
PORT="$(jq -r '.port // ""' "$CONFIG_PATH")"
USER="$(jq -r '.user // ""' "$CONFIG_PATH")"
PASS="$(jq -r '.pass // ""' "$CONFIG_PATH")"
THREADS="$(jq -r '.threads // 0' "$CONFIG_PATH")"
PRIO="$(jq -r '.priority // 0' "$CONFIG_PATH")"

# Normalizácia POOL:
# - ak user zadá "pool.supportxmr.com:443", rozsekneme to
# - ak user zadá "stratum+ssl://pool.supportxmr.com:443", odstránime scheme
# - ak user zadá iba host, necháme port zvlášť
POOL_CLEAN="$(echo "$POOL" | sed 's#^[a-zA-Z0-9+.-]*://##')"

# Ak je POOL vo forme host:port, rozdeľ:
if echo "$POOL_CLEAN" | grep -q ':'; then
  POOL_HOST="$(echo "$POOL_CLEAN" | awk -F: '{print $1}')"
  POOL_PORT_FROM_POOL="$(echo "$POOL_CLEAN" | awk -F: '{print $2}')"
else
  POOL_HOST="$POOL_CLEAN"
  POOL_PORT_FROM_POOL=""
fi

# Port: preferuj explicitné .port, inak zober z pool host:port, inak default 3333
if [ -n "$PORT" ] && [ "$PORT" != "null" ]; then
  POOL_PORT="$PORT"
elif [ -n "$POOL_PORT_FROM_POOL" ]; then
  POOL_PORT="$POOL_PORT_FROM_POOL"
else
  POOL_PORT="3333"
fi

# Minimálne sanity checky
if [ -z "$POOL_HOST" ]; then
  echo "[xmrig-addon] ERROR: pool is empty"
  exit 1
fi

if [ -z "$USER" ]; then
  echo "[xmrig-addon] ERROR: user is empty"
  exit 1
fi

echo "[xmrig-addon] Starting XMRig on ${POOL_HOST}:${POOL_PORT} threads=${THREADS} prio=${PRIO}"

# MSR: nič NEVYTVÁRAŤ cez mknod.
# Ak je device správne namapovaný a add-on má SYS_RAWIO, xmrig si MSR mod aplikuje sám.
if [ -c /dev/cpu/0/msr ]; then
  echo "[xmrig-addon] MSR device present: /dev/cpu/0/msr"
else
  echo "[xmrig-addon] WARNING: MSR device missing: /dev/cpu/0/msr"
fi

# TLS podľa portu (443 zvyčajne TLS, ale nechávam logiku ako si mal)
TLS_ARGS=""
if [ "$POOL_PORT" = "443" ]; then
  TLS_ARGS="--tls"
fi

# threads: ak 0, xmrig si zvolí sám; ak >0, nastavíme explicitne
THREAD_ARGS=""
if [ "$THREADS" -gt 0 ] 2>/dev/null; then
  THREAD_ARGS="--threads=${THREADS}"
fi

# prio: ak 0, nepchám flag; ak >0, nastavím
PRIO_ARGS=""
if [ "$PRIO" -gt 0 ] 2>/dev/null; then
  PRIO_ARGS="--cpu-priority=${PRIO}"
fi

# Spustenie
exec /usr/bin/xmrig \
  --url "${POOL_HOST}:${POOL_PORT}" \
  --user "$USER" \
  --pass "$PASS" \
  $TLS_ARGS \
  $THREAD_ARGS \
  $PRIO_ARGS \
  --randomx-mode=fast
