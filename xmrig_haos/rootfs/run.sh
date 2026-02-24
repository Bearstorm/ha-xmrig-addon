
#!/bin/sh
set -eu

CONFIG_PATH="/data/options.json"

POOL="$(jq -r '.pool // ""' "$CONFIG_PATH")"
PORT="$(jq -r '.port // 0' "$CONFIG_PATH")"
WALLET="$(jq -r '.wallet // ""' "$CONFIG_PATH")"
WORKER="$(jq -r '.worker // ""' "$CONFIG_PATH")"
THREADS="$(jq -r '.threads // 0' "$CONFIG_PATH")"
PRIO="$(jq -r '.priority // 0' "$CONFIG_PATH")"

if [ -z "$POOL" ]; then
  echo "[xmrig-haos] ERROR: pool is empty"
  exit 1
fi

if [ -z "$WALLET" ]; then
  echo "[xmrig-haos] ERROR: wallet is empty"
  exit 1
fi

echo "[xmrig-haos] Starting SAFE XMRig (no MSR, no host access)"
echo "[xmrig-haos] Pool: ${POOL}:${PORT}"
echo "[xmrig-haos] Worker: ${WORKER}"

exec /usr/bin/xmrig \
  --url "${POOL}:${PORT}" \
  --user "$WALLET" \
  --pass "$WORKER" \
  --threads="$THREADS" \
  --cpu-priority="$PRIO" \
  --randomx-mode=fast \
  --randomx-wrmsr=0 \
  --randomx-no-rdmsr \
  --randomx-init=0
