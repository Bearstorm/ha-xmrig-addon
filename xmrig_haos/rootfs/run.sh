
#!/bin/sh

echo "[xmrig-addon] run.sh script started..."

# Nastavíme len -u, aby sme mohli zachytiť pád Step 1
set -u

CONFIG_PATH="/data/options.json"

# Načítanie premenných cez jq
POOL=$(jq -r '.pool // ""' "$CONFIG_PATH")
PORT=$(jq -r '.port // 0' "$CONFIG_PATH")
WALLET=$(jq -r '.wallet // ""' "$CONFIG_PATH")
WORKER=$(jq -r '.worker // ""' "$CONFIG_PATH")
THREADS=$(jq -r '.threads // 0' "$CONFIG_PATH")
PRIO=$(jq -r '.priority // 0' "$CONFIG_PATH")

# Čistenie a príprava URL
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

# Dynamické argumenty
TLS_ARGS=""
[ "$POOL_PORT" = "443" ] && TLS_ARGS="--tls"

THREAD_ARGS=""
[ "$THREADS" -gt 0 ] && THREAD_ARGS="--threads=${THREADS}"

PRIO_ARGS=""
[ "$PRIO" -gt 0 ] && PRIO_ARGS="--cpu-priority=${PRIO}"

# --- TO NAJDÔLEŽITEJŠIE: SAFE ARGUMENTY (prevzaté z tvojho funkčného skriptu) ---
# Vypneme všetko, čo v Safe móde nejde, aby neboli errory v logu
SAFE_MSR_ARGS="--randomx-wrmsr=0 --randomx-no-rdmsr --randomx-init=0 --no-huge-pages --keepalive"

echo "[xmrig-addon] Step 1: Trying FAST mode (2.3 GB RAM)..."

# Prvý pokus - FAST
/usr/bin/xmrig \
  --url "${POOL_HOST}:${POOL_PORT}" \
  --user "$WALLET" \
  --pass "$WORKER" \
  $TLS_ARGS \
  $THREAD_ARGS \
  $PRIO_ARGS \
  $SAFE_MSR_ARGS \
  --randomx-mode=fast

# Ak prvý pokus zlyhal (málo RAM), prepni na LIGHT
if [ $? -ne 0 ]; then
  echo "[xmrig-addon] FAST mode failed. Falling back to LIGHT mode..."
  
  exec /usr/bin/xmrig \
    --url "${POOL_HOST}:${POOL_PORT}" \
    --user "$WALLET" \
    --pass "$WORKER" \
    $TLS_ARGS \
    $THREAD_ARGS \
    $PRIO_ARGS \
    $SAFE_MSR_ARGS \
    --randomx-mode=light
fi
