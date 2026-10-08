
#!/bin/bash
set -euo pipefail

# --------------------------------------------------
# 1. Logging and error handling
# --------------------------------------------------

log() {
    printf '[xmrig-addon] %s\n' "$*"
}

fail() {
    printf '[xmrig-addon] ERROR: %s\n' "$*" >&2
    exit 1
}

# --------------------------------------------------
# 2. Production paths and isolated test mode
# --------------------------------------------------

CONFIG_PATH=/data/options.json
XMRIG_BIN=/usr/bin/xmrig
MEMINFO_PATH=/proc/meminfo
CGROUP_MAX_PATH=/sys/fs/cgroup/memory.max
CGROUP_CURRENT_PATH=/sys/fs/cgroup/memory.current

# Test mode is opt-in and not configured by the add-on.
# It must only be used in an isolated test environment.

if [[ "${XMRIG_TEST_MODE:-0}" == 1 ]]; then
    CONFIG_PATH="${XMRIG_TEST_CONFIG:?Missing test configuration path}"
    XMRIG_BIN="${XMRIG_TEST_BINARY:?Missing test executable path}"
    MEMINFO_PATH="${XMRIG_TEST_MEMINFO:?Missing test meminfo path}"
    CGROUP_MAX_PATH="${XMRIG_TEST_CGROUP_MAX:?Missing test cgroup max path}"
    CGROUP_CURRENT_PATH="${XMRIG_TEST_CGROUP_CURRENT:?Missing test cgroup current path}"

    log "TEST MODE: substituting paths; no real miner should be configured here"
fi

# --------------------------------------------------
# 3. Validate dependencies and configuration
# --------------------------------------------------

command -v jq >/dev/null 2>&1 ||
    fail "jq is not installed"

[[ -x "$XMRIG_BIN" ]] ||
    fail "XMRig executable not found"

[[ -f "$CONFIG_PATH" ]] ||
    fail "Configuration file is missing"

jq -e 'type == "object"' "$CONFIG_PATH" >/dev/null ||
    fail "Invalid JSON configuration"

# --------------------------------------------------
# 4. Load configuration
# --------------------------------------------------

POOL=$(jq -r '.pool // ""' "$CONFIG_PATH")
PORT=$(jq -r '.port // 0' "$CONFIG_PATH")
WALLET=$(jq -r '.wallet // ""' "$CONFIG_PATH")
WORKER=$(jq -r '.worker // ""' "$CONFIG_PATH")
THREADS=$(jq -r '.threads // 2' "$CONFIG_PATH")
PRIO=$(jq -r '.priority // 2' "$CONFIG_PATH")

# --------------------------------------------------
# 5. Validate user configuration
# --------------------------------------------------

[[ -n "$POOL" && "$POOL" != null ]] ||
    fail "Mining pool is empty"

[[ -n "$WALLET" && "$WALLET" != null ]] ||
    fail "Wallet address is empty"

[[ "$POOL" != *[[:space:]]* ]] ||
    fail "Pool address contains whitespace"

[[ "$POOL" != *'@'* && "$POOL" != *'?'* && "$POOL" != *'#'* ]] ||
    fail "Pool address contains unexpected characters"

validate_number() {
    local value=$1 min=$2 max=$3 label=$4
    local max_digits=${#max}

    [[ "$value" =~ ^[0-9]+$ && ${#value} -le $max_digits ]] ||
        fail "Invalid $label"

    local number=$((10#$value))

    (( number >= min && number <= max )) ||
        fail "$label must be between $min and $max"

    printf '%s' "$number"
}

PORT=$(validate_number "$PORT" 1 65535 "pool port")
THREADS=$(validate_number "$THREADS" 1 256 "CPU threads")
PRIO=$(validate_number "$PRIO" 0 5 "CPU priority")

[[ "$WORKER" != *$'\n'* && "$WORKER" != *$'\r'* ]] ||
    fail "Invalid worker name"

# --------------------------------------------------
# 6. Parse pool address
# --------------------------------------------------

# Accept:
# hostname
# hostname:port
# [IPv6]
# [IPv6]:port
#
# An explicit port option always takes precedence.

POOL_HOST=$POOL

if [[ "$POOL_HOST" == *://* ]]; then
    POOL_HOST=${POOL_HOST#*://}
fi

POOL_HOST=${POOL_HOST%/}

[[ "$POOL_HOST" != */* ]] ||
    fail "Pool address must not contain a path"

if [[ "$POOL_HOST" == \[* ]]; then

    if [[ "$POOL_HOST" =~ ^\[([^]]+)\](:([0-9]+))?$ ]]; then
        POOL_HOST="[${BASH_REMATCH[1]}]"
    else
        fail "Invalid bracketed IPv6 pool address"
    fi

elif [[ "$POOL_HOST" == *:* ]]; then

    [[ "$POOL_HOST" == *:* && "$POOL_HOST" != *:*:* ]] ||
        fail "IPv6 addresses must use brackets"

    POOL_HOST=${POOL_HOST%%:*}
fi

[[ -n "$POOL_HOST" && "$POOL_HOST" != *[[:space:]]* ]] ||
    fail "Invalid pool hostname"

# --------------------------------------------------
# 7. Configure TLS
# --------------------------------------------------

TLS_ARGS=()

# Preserve legacy TLS behavior for now.
# Explicit TLS configuration will be added later.

if (( PORT == 443 )); then
    TLS_ARGS+=(--tls)
    log "TLS enabled (legacy port 443 rule)"
else
    log "TLS disabled (legacy port rule)"
fi

# --------------------------------------------------
# 8. Detect available memory
# --------------------------------------------------

AVAILABLE_BYTES=0

if [[ -r "$MEMINFO_PATH" ]]; then

    MEM_KB=$(awk '/^MemAvailable:/ {print $2; exit}' "$MEMINFO_PATH")

    if [[ "$MEM_KB" =~ ^[0-9]+$ && ${#MEM_KB} -le 15 ]]; then
        AVAILABLE_BYTES=$((MEM_KB * 1024))
    fi
fi

# Respect cgroup v2 memory limits when present.

if [[ -r "$CGROUP_MAX_PATH" && -r "$CGROUP_CURRENT_PATH" ]]; then

    CGROUP_MAX=$(<"$CGROUP_MAX_PATH")
    CGROUP_USED=$(<"$CGROUP_CURRENT_PATH")

    if [[ "$CGROUP_MAX" =~ ^[0-9]+$ &&
          "$CGROUP_USED" =~ ^[0-9]+$ &&
          ${#CGROUP_MAX} -le 18 &&
          ${#CGROUP_USED} -le 18 ]]; then

        CGROUP_AVAILABLE=0

        if (( CGROUP_MAX > CGROUP_USED )); then
            CGROUP_AVAILABLE=$((CGROUP_MAX - CGROUP_USED))
        fi

        if (( AVAILABLE_BYTES == 0 ||
              CGROUP_AVAILABLE < AVAILABLE_BYTES )); then

            AVAILABLE_BYTES=$CGROUP_AVAILABLE
        fi
    fi
fi

# --------------------------------------------------
# 9. Select RandomX mode
# --------------------------------------------------

FAST_MIN_BYTES=$((3 * 1024 * 1024 * 1024))

if (( AVAILABLE_BYTES >= FAST_MIN_BYTES )); then
    RANDOMX_MODE=fast
else
    RANDOMX_MODE=light
fi

# --------------------------------------------------
# 10. Prepare miner arguments
# --------------------------------------------------

log "Pool: ${POOL_HOST}:${PORT}"
log "Worker: $WORKER"
log "CPU threads: $THREADS; priority: $PRIO"
log "Available memory: $((AVAILABLE_BYTES / 1024 / 1024)) MiB"
log "RandomX mode: $RANDOMX_MODE"
log "MSR and huge pages: disabled"

# Never print wallet credentials to the log.

ARGS=(
    --url "${POOL_HOST}:${PORT}"
    --user "$WALLET"
    --pass "$WORKER"
    --threads="$THREADS"
    --cpu-priority="$PRIO"
    --randomx-wrmsr=-1
    --randomx-no-rdmsr
    --no-huge-pages
    --keepalive
    --randomx-mode="$RANDOMX_MODE"
)

ARGS+=("${TLS_ARGS[@]}")

# --------------------------------------------------
# 11. Start XMRig
# --------------------------------------------------

# In production, this executes /usr/bin/xmrig.
# In isolated tests, a mock executable is used.

exec "$XMRIG_BIN" "${ARGS[@]}"
