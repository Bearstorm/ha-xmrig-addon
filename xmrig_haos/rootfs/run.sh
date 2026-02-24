
#!/bin/sh

# Výpis hneď po štarte, aby sme videli, že skript žije
echo "[xmrig-addon] run.sh script started..."

# Nastavíme len -u (pád pri nedefinovanej premennej), nie -e
set -u

CONFIG_PATH="/data/options.json"

# Načítanie premenných
POOL=$(jq -r '.pool // ""' "$CONFIG_PATH")
PORT=$(jq -r '.port // 0' "$CONFIG_PATH")
WALLET=$(jq -r '.wallet // ""' "$CONFIG_PATH")
WORKER=$(jq -r '.worker // ""' "$CONFIG_PATH")
THREADS=$(jq -r '.threads // 0' "$CONFIG_PATH")
PRIO=$(jq -r '.priority // 0' "$CONFIG_PATH")

# Čistenie URL
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

# Kontrola povinných údajov
if [ -z "$POOL_HOST" ] || [ "$POOL_HOST" = "null" ]; then
  echo "[xmrig-addon] ERROR: pool is empty"
  exit 1
fi

if [ -z "$WALLET" ] || [ "$WALLET" = "null" ]; then
  echo "[xmrig-addon] ERROR: wallet is empty"
  exit 1
fi

echo "[xmrig-addon] (HAOS Safe) Starting XMRig on ${POOL_HOST}:${POOL_PORT}"

# Argumenty
TLS_ARGS=""
[ "$POOL_PORT" = "443" ] && TLS_ARGS="--tls"

THREAD_ARGS=""
[ "$THREADS" -gt 0 ] && THREAD_ARGS="--threads=${THREADS}"

PRIO_ARGS=""
[ "$PRIO" -gt 0 ] && PRIO_ARGS="--cpu-priority=${PRIO}"

# OPRAVENÉ Parametre pre čistý log v HAOS Safe
# XMRig vyžaduje --cpu-no-msr (nie no-cpu-msr)
SAFE_PARAMS="--cpu-no-msr --no-huge-pages --randomx-no-rdmsr --keepalive"

echo "[xmrig-addon] Step 1: Trying FAST mode..."

# Prvý pokus - FAST
/usr/bin/xmrig \
  --url "${POOL_HOST}:${POOL_PORT}" \
  --user "$WALLET" \
  --pass "$WORKER" \
  $TLS_ARGS \
  $THREAD_ARGS \
  $PRIO_ARGS \
  --randomx-mode=fast \
  $SAFE_PARAMS

# Ak prvý pokus zlyhal (exit code nie je 0)
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
    $SAFE_PARAMS
fi
