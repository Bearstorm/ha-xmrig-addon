#!/usr/bin/with-contenv bash
set -euo pipefail

CONFIG_PATH="/data/options.json"

POOL="$(jq -r '.pool' "${CONFIG_PATH}")"
USER="$(jq -r '.user' "${CONFIG_PATH}")"
PASS="$(jq -r '.pass' "${CONFIG_PATH}")"
TLS="$(jq -r '.tls' "${CONFIG_PATH}")"
ALGO="$(jq -r '.algo' "${CONFIG_PATH}")"
THREADS="$(jq -r '.threads' "${CONFIG_PATH}")"
DONATE="$(jq -r '.donate' "${CONFIG_PATH}")"

HTTP_ENABLED="$(jq -r '.http_enabled' "${CONFIG_PATH}")"
HTTP_HOST="$(jq -r '.http_host' "${CONFIG_PATH}")"
HTTP_PORT="$(jq -r '.http_port' "${CONFIG_PATH}")"
HTTP_ACCESS_TOKEN="$(jq -r '.http_access_token // ""' "${CONFIG_PATH}")"
HTTP_RESTRICTED="$(jq -r '.http_restricted' "${CONFIG_PATH}")"

LOG_LEVEL="$(jq -r '.log_level' "${CONFIG_PATH}")"

# Build XMRig args
ARGS=()
ARGS+=("-o" "${POOL}")
ARGS+=("-u" "${USER}")
ARGS+=("-p" "${PASS}")
ARGS+=("--donate-level=${DONATE}")
ARGS+=("--algo=${ALGO}")

if [[ "${TLS}" == "true" ]]; then
  ARGS+=("--tls")
fi

if [[ "${THREADS}" -gt 0 ]]; then
  ARGS+=("--threads=${THREADS}")
fi

if [[ "${HTTP_ENABLED}" == "true" ]]; then
  ARGS+=("--http-host=${HTTP_HOST}")
  ARGS+=("--http-port=${HTTP_PORT}")

  if [[ -n "${HTTP_ACCESS_TOKEN}" && "${HTTP_ACCESS_TOKEN}" != "null" ]]; then
    ARGS+=("--http-access-token=${HTTP_ACCESS_TOKEN}")
  fi

  # restricted=true znamená obmedzené API (ak je token nastavený) :contentReference[oaicite:1]{index=1}
  if [[ "${HTTP_RESTRICTED}" == "true" ]]; then
    ARGS+=("--http-restricted")
  else
    ARGS+=("--no-http-restricted")
  fi
fi

# log level mapping (xmrig používa --verbose/--log-level podľa buildu; necháme len --verbose pre debug/trace)
if [[ "${LOG_LEVEL}" == "debug" || "${LOG_LEVEL}" == "trace" ]]; then
  ARGS+=("--verbose")
fi

echo "[xmrig-addon] Starting XMRig..."
echo "[xmrig-addon] Pool: ${POOL}"
echo "[xmrig-addon] Algo: ${ALGO}, Threads: ${THREADS}, Donate: ${DONATE}"
echo "[xmrig-addon] HTTP API: ${HTTP_ENABLED} (${HTTP_HOST}:${HTTP_PORT})"

# Info check (pomôže diagnostike MSR)
if [[ -e /dev/cpu/0/msr ]]; then
  echo "[xmrig-addon] /dev/cpu/0/msr exists"
else
  echo "[xmrig-addon] /dev/cpu/0/msr MISSING"
fi

exec xmrig "${ARGS[@]}"
