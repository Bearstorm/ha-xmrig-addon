
#!/usr/bin/env bash
set -euo pipefail

# ==================================================
# XMRig HAOS Safe - Functional Tests
#
# Tests the real startup script with:
# - temporary configuration files
# - simulated system memory
# - simulated cgroup limits
# - a mock XMRig executable
#
# No real mining is performed.
# ==================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SCRIPT="${ROOT_DIR}/xmrig_haos/rootfs/run.sh"

PASS=0
FAIL=0

TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT

CONFIG_FILE="${TEST_DIR}/options.json"
MEMINFO_FILE="${TEST_DIR}/meminfo"
CGROUP_MAX_FILE="${TEST_DIR}/memory.max"
CGROUP_CURRENT_FILE="${TEST_DIR}/memory.current"
MOCK_XMRIG="${TEST_DIR}/xmrig"
OUTPUT_FILE="${TEST_DIR}/output.log"
ARGS_FILE="${TEST_DIR}/xmrig-args.log"

# --------------------------------------------------
# 1. Check prerequisites
# --------------------------------------------------

command -v bash >/dev/null ||
    { echo "ERROR: bash missing"; exit 1; }

command -v jq >/dev/null ||
    { echo "ERROR: jq missing"; exit 1; }

[[ -f "$RUN_SCRIPT" ]] ||
    { echo "ERROR: run.sh not found"; exit 1; }

bash -n "$RUN_SCRIPT"

# --------------------------------------------------
# 2. Create mock miner
# --------------------------------------------------

cat > "$MOCK_XMRIG" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

: "${MOCK_ARGS_FILE:?}"

printf '%s\n' "$@" > "$MOCK_ARGS_FILE"
echo "MOCK_XMRIG_EXECUTED"

exit 0
MOCK

chmod 0755 "$MOCK_XMRIG"

# --------------------------------------------------
# 3. Test helpers
# --------------------------------------------------

set_memory() {
    local available_kib="$1"
    local cgroup_max="$2"
    local cgroup_used="$3"

    printf 'MemAvailable: %s kB\n' \
        "$available_kib" > "$MEMINFO_FILE"

    printf '%s\n' "$cgroup_max" > "$CGROUP_MAX_FILE"
    printf '%s\n' "$cgroup_used" > "$CGROUP_CURRENT_FILE"
}

set_config() {
    local pool="$1"
    local port="$2"
    local wallet="$3"
    local worker="$4"
    local threads="$5"
    local priority="$6"

    jq -n \
        --arg pool "$pool" \
        --arg port "$port" \
        --arg wallet "$wallet" \
        --arg worker "$worker" \
        --arg threads "$threads" \
        --arg priority "$priority" \
        '{
            pool: $pool,
            port: $port,
            wallet: $wallet,
            worker: $worker,
            threads: $threads,
            priority: $priority
        }' > "$CONFIG_FILE"
}

default_config() {
    set_config \
        "pool.example.org" \
        "443" \
        "TEST_WALLET_ONLY" \
        "HA-Test" \
        "2" \
        "2"
}

default_memory() {
    set_memory \
        8388608 \
        max \
        0
}

run_miner() {
    rm -f "$ARGS_FILE"

    XMRIG_TEST_MODE=1 \
    XMRIG_TEST_CONFIG="$CONFIG_FILE" \
    XMRIG_TEST_BINARY="$MOCK_XMRIG" \
    XMRIG_TEST_MEMINFO="$MEMINFO_FILE" \
    XMRIG_TEST_CGROUP_MAX="$CGROUP_MAX_FILE" \
    XMRIG_TEST_CGROUP_CURRENT="$CGROUP_CURRENT_FILE" \
    MOCK_ARGS_FILE="$ARGS_FILE" \
        bash "$RUN_SCRIPT" > "$OUTPUT_FILE" 2>&1
}

assert_arg() {
    [[ -f "$ARGS_FILE" ]] || return 1
    grep -Fxq -- "$1" "$ARGS_FILE"
}

assert_no_arg() {
    [[ -f "$ARGS_FILE" ]] || return 1
    ! grep -Fxq -- "$1" "$ARGS_FILE"
}

assert_output() {
    grep -Fq -- "$1" "$OUTPUT_FILE"
}

pass() {
    PASS=$((PASS + 1))
    echo "PASS: $1"
}

fail() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1"
    echo "--- Test output ---"
    cat "$OUTPUT_FILE" 2>/dev/null || true
    echo "-------------------"
}

# --------------------------------------------------
# 4. Functional tests
# --------------------------------------------------

echo "======================================"
echo "XMRig HAOS Safe - Functional Tests"
echo "======================================"

# TEST 01 - FAST mode

default_config
default_memory

if run_miner &&
   assert_arg "--randomx-mode=fast" &&
   assert_output "MOCK_XMRIG_EXECUTED"; then
    pass "FAST mode with sufficient RAM"
else
    fail "FAST mode with sufficient RAM"
fi

# TEST 02 - LIGHT mode

default_config
set_memory 524288 max 0

if run_miner &&
   assert_arg "--randomx-mode=light"; then
    pass "LIGHT mode with insufficient RAM"
else
    fail "LIGHT mode with insufficient RAM"
fi

# TEST 03 - Cgroup memory limit

default_config
set_memory \
    8388608 \
    1073741824 \
    268435456

if run_miner &&
   assert_arg "--randomx-mode=light"; then
    pass "Cgroup memory limit respected"
else
    fail "Cgroup memory limit respected"
fi

# TEST 04 - TLS on port 443

default_config
default_memory

if run_miner &&
   assert_arg "--tls"; then
    pass "TLS enabled on port 443"
else
    fail "TLS enabled on port 443"
fi

# TEST 05 - No TLS on port 3333

set_config \
    "pool.example.org" \
    "3333" \
    "TEST_WALLET_ONLY" \
    "HA-Test" \
    "2" \
    "2"

default_memory

if run_miner &&
   assert_no_arg "--tls"; then
    pass "TLS disabled on port 3333"
else
    fail "TLS disabled on port 3333"
fi

# TEST 06 - CPU configuration

set_config \
    "pool.example.org" \
    "443" \
    "TEST_WALLET_ONLY" \
    "HA-Test" \
    "4" \
    "3"

default_memory

if run_miner &&
   assert_arg "--threads=4" &&
   assert_arg "--cpu-priority=3" &&
   assert_arg "HA-Test"; then
    pass "CPU threads, priority and worker"
else
    fail "CPU threads, priority and worker"
fi

# TEST 07 - Empty wallet rejected

set_config \
    "pool.example.org" \
    "443" \
    "" \
    "HA-Test" \
    "2" \
    "2"

default_memory

if ! run_miner; then
    if assert_output "Wallet address is empty" &&
       [[ ! -f "$ARGS_FILE" ]]; then
        pass "Empty wallet rejected"
    else
        fail "Empty wallet rejected"
    fi
else
    fail "Empty wallet rejected"
fi

# TEST 08 - Invalid port rejected

set_config \
    "pool.example.org" \
    "99999" \
    "TEST_WALLET_ONLY" \
    "HA-Test" \
    "2" \
    "2"

if ! run_miner; then
    if [[ ! -f "$ARGS_FILE" ]]; then
        pass "Invalid port rejected"
    else
        fail "Invalid port rejected"
    fi
else
    fail "Invalid port rejected"
fi

# TEST 09 - Invalid CPU threads rejected

set_config \
    "pool.example.org" \
    "443" \
    "TEST_WALLET_ONLY" \
    "HA-Test" \
    "0" \
    "2"

if ! run_miner; then
    if [[ ! -f "$ARGS_FILE" ]]; then
        pass "Invalid CPU thread count rejected"
    else
        fail "Invalid CPU thread count rejected"
    fi
else
    fail "Invalid CPU thread count rejected"
fi

# TEST 10 - Invalid priority rejected

set_config \
    "pool.example.org" \
    "443" \
    "TEST_WALLET_ONLY" \
    "HA-Test" \
    "2" \
    "9"

if ! run_miner; then
    if [[ ! -f "$ARGS_FILE" ]]; then
        pass "Invalid CPU priority rejected"
    else
        fail "Invalid CPU priority rejected"
    fi
else
    fail "Invalid CPU priority rejected"
fi

# TEST 11 - Invalid pool path rejected

set_config \
    "pool.example.org/path" \
    "443" \
    "TEST_WALLET_ONLY" \
    "HA-Test" \
    "2" \
    "2"

if ! run_miner; then
    if [[ ! -f "$ARGS_FILE" ]]; then
        pass "Invalid pool path rejected"
    else
        fail "Invalid pool path rejected"
    fi
else
    fail "Invalid pool path rejected"
fi

# TEST 12 - Pool address with embedded port

set_config \
    "pool.example.org:3333" \
    "443" \
    "TEST_WALLET_ONLY" \
    "HA-Test" \
    "2" \
    "2"

default_memory

if run_miner &&
   assert_arg "pool.example.org:443" &&
   assert_arg "--tls"; then
    pass "Configured port overrides embedded port"
else
    fail "Configured port overrides embedded port"
fi

# TEST 13 - Safe mining arguments

default_config
default_memory

if run_miner &&
   assert_arg "--randomx-wrmsr=-1" &&
   assert_arg "--randomx-no-rdmsr" &&
   assert_arg "--no-huge-pages" &&
   assert_arg "--keepalive"; then
    pass "Safe XMRig arguments"
else
    fail "Safe XMRig arguments"
fi

# TEST 14 - Wallet not printed in logs

default_config
default_memory

if run_miner &&
   ! grep -Fq "TEST_WALLET_ONLY" "$OUTPUT_FILE"; then
    pass "Wallet credentials not exposed in logs"
else
    fail "Wallet credentials not exposed in logs"
fi

# --------------------------------------------------
# 5. Final summary
# --------------------------------------------------

echo
echo "======================================"
echo "Functional test results"
echo "======================================"
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo "Total:  $((PASS + FAIL))"
echo "======================================"

if (( FAIL > 0 )); then
    exit 1
fi

echo "All functional tests passed."
exit 0
