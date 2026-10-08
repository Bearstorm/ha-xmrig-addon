
#!/bin/bash

set -euo pipefail

echo "[xmrig-addon] Starting XMRig HAOS Safe..."
echo "[xmrig-addon] XMRig core: 6.26.0"

CONFIG_PATH="/data/options.json"

# --------------------------------------------------
# 1. Logging and error handling
# --------------------------------------------------

log() {
    echo "[xmrig-addon] $*"
}

error() {
    echo "[xmrig-addon] ERROR: $*" >&2
    exit 1
}

# --------------------------------------------------
# 2. Check dependencies and configuration
# --------------------------------------------------

command -v jq >/dev/null 2>&1 ||
    error "jq is not installed"

command -v xmrig >/dev/null 2>&1 ||
    error "XMRig binary not found"

[ -f "$CONFIG_PATH" ] ||
    error "Configuration file not found: $CONFIG_PATH"

jq -e 'type == "object"' "$CONFIG_PATH" >/dev/null ||
    error "Invalid JSON configuration"

# --------------------------------------------------
# 3. Load options
# --------------------------------------------------

POOL=$(jq -r '.pool // ""' "$CONFIG_PATH")
PORT=$(jq -r '.port // 0' "$CONFIG_PATH")
WALLET=$(jq -r '.wallet // ""' "$CONFIG_PATH")
WORKER=$(jq -r '.worker // ""' "$CONFIG_PATH")
THREADS=$(jq -r '.threads // 2' "$CONFIG_PATH")
PRIO=$(jq -r '.priority // 2' "$CONFIG_PATH")

# --------------------------------------------------
# 4. Validate configuration
# --------------------------------------------------

[[ -n "$POOL" ]] ||
    error "Mining pool is empty"

[[ -n "$WALLET" ]] ||
    error "Wallet address is empty"

[[ "$PORT" =~ ^[0-9]+$ ]] ||
    error "Invalid pool port"

(( 10#$PORT >= 1 && 10#$PORT <= 65535 )) ||
    error "Pool port must be between 1 and 65535"

[[ "$THREADS" =~ ^[0-9]+$ ]] ||
    error "Invalid CPU thread count"

(( 10#$THREADS >= 1 && 10#$THREADS <= 256 )) ||
    error "CPU threads must be between 1 and 256"

[[ "$PRIO" =~ ^[0-9]+$ ]] ||
    error "Invalid CPU priority"

(( 10#$PRIO >= 0 && 10#$PRIO <= 5 )) ||
    error "CPU priority must be between 0 and 5"

# Normalize numerical options
PORT=$((10#$PORT))
THREADS=$((10#$THREADS))
PRIO=$((10#$PRIO))

# --------------------------------------------------
# 5. Parse pool address
# --------------------------------------------------

POOL_CLEAN="$POOL"

# Accept plain hostnames and URLs with a scheme
if [[ "$POOL_CLEAN" == *"://"* ]]; then
    POOL_CLEAN="${POOL_CLEAN#*://}"
fi

# Remove trailing slash
POOL_CLEAN="${POOL_CLEAN%/}"

# Do not allow URL paths
[[ "$POOL_CLEAN" != */* ]] ||
    error "Mining pool must not contain a URL path"

POOL_HOST="$POOL_CLEAN"

# Support hostname:port and bracketed IPv6
if [[ "$POOL_CLEAN" == \[*\]* ]]; then
    POOL_HOST="${POOL_CLEAN%%]*}]"

    if [[ "$POOL_CLEAN" =~ ^\[([^]]+)\]:([0-9]+)$ ]]; then
        POOL_HOST="[${BASH_REMATCH[1]}]"
        log "Embedded pool port detected; using configured port"
    elif [[ "$POOL_CLEAN" =~ ^\[([^]]+)\]$ ]]; then
        POOL_HOST="$POOL_CLEAN"
    else
        error "Invalid IPv6 pool address"
    fi

elif [[ "$POOL_CLEAN" == *:* ]]; then
    POOL_HOST="${POOL_CLEAN%%:*}"
    log "Embedded pool port detected; using configured port"
fi

[[ -n "$POOL_HOST" ]] ||
    error "Mining pool hostname is empty"

[[ "$POOL_HOST" != *[[:space:]]* ]] ||
    error "Mining pool hostname contains whitespace"

log "Pool: ${POOL_HOST}:${PORT}"
log "Worker: ${WORKER}"
log "CPU threads: ${THREADS}"
log "CPU priority: ${PRIO}"

# Wallet and other credentials are never logged.

# --------------------------------------------------
# 6. Configure TLS
# --------------------------------------------------

TLS_ARGS=()

# Legacy behavior; configurable TLS comes next.
if (( PORT == 443 )); then
    TLS_ARGS+=(--tls)
    log "TLS enabled (legacy port 443 rule)"
else
    log "TLS disabled (legacy port rule)"
fi

# --------------------------------------------------
# 7. Safe XMRig options
# --------------------------------------------------

XMRIG_ARGS=(
    --url "${POOL_HOST}:${PORT}"
    --user "$WALLET"
    --pass "$WORKER"
    --threads="$THREADS"
    --cpu-priority="$PRIO"
    --randomx-wrmsr=-1
    --randomx-no-rdmsr
    --no-huge-pages
    --keepalive
)

XMRIG_ARGS+=("${TLS_ARGS[@]}")

# --------------------------------------------------
# 8. Detect available system memory
# --------------------------------------------------

# FAST needs approximately 2.3 GB for RandomX.
# Reserve additional memory for the operating system.
FAST_MIN_BYTES=$((3 * 1024 * 1024 * 1024))

AVAILABLE_BYTES=0

if [[ -r /proc/meminfo ]]; then
    MEM_KB=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)

    if [[ "$MEM_KB" =~ ^[0-9]+$ ]]; then
        AVAILABLE_BYTES=$((MEM_KB * 1024))
    fi
fi

# Respect cgroup v2 memory limits when present.
if [[ -r /sys/fs/cgroup/memory.max &&
      -r /sys/fs/cgroup/memory.current ]]; then

    CGROUP_MAX=$(cat /sys/fs/cgroup/memory.max)
    CGROUP_USED=$(cat /sys/fs/cgroup/memory.current)

    if [[ "$CGROUP_MAX" =~ ^[0-9]+$ &&
          "$CGROUP_USED" =~ ^[0-9]+$ ]]; then

        if (( CGROUP_MAX > CGROUP_USED )); then
            CGROUP_AVAILABLE=$((CGROUP_MAX - CGROUP_USED))
        else
            CGROUP_AVAILABLE=0
        fi

        if (( AVAILABLE_BYTES == 0 ||
              CGROUP_AVAILABLE < AVAILABLE_BYTES )); then
            AVAILABLE_BYTES=$CGROUP_AVAILABLE
        fi
    fi
fi

AVAILABLE_MB=$((AVAILABLE_BYTES / 1024 / 1024))

log "Detected available memory: ${AVAILABLE_MB} MiB"

# --------------------------------------------------
# 9. Select RandomX mode before starting
# --------------------------------------------------

if (( AVAILABLE_BYTES >= FAST_MIN_BYTES )); then
    RANDOMX_MODE="fast"
    log "Selected RandomX FAST mode"
else
    RANDOMX_MODE="light"
    log "Selected RandomX LIGHT mode"
    log "Reason: available memory below 3 GiB or unknown"
fi

XMRIG_ARGS+=("--randomx-mode=${RANDOMX_MODE}")

# --------------------------------------------------
# 10. Start miner
# --------------------------------------------------

log "Starting XMRig..."
log "RandomX mode: ${RANDOMX_MODE}"
log "MSR optimization: disabled"
log "Huge pages: disabled"

# Do not automatically switch modes after a crash.
# Configuration, network and runtime errors must
# remain visible for diagnosis.

exec /usr/bin/xmrig "${XMRIG_ARGS[@]}"
