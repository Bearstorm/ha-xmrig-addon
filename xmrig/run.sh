#!/usr/bin/with-contenv bashio

POOL=$(bashio::config 'pool')
USER=$(bashio::config 'user')
PASS=$(bashio::config 'pass')

bashio::log.info "Starting Bearstorm Miner on pool: ${POOL}"

# Pridanie 'exec' zabezpečí, že xmrig prevezme PID od skriptu a stane sa hlavným procesom
exec /usr/bin/xmrig --url "$POOL" --user "$USER" --pass "$PASS"
