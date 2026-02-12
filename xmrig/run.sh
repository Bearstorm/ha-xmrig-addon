#!/usr/bin/with-contenv bashio

POOL=$(bashio::config 'pool')
USER=$(bashio::config 'user')
PASS=$(bashio::config 'pass')

bashio::log.info "Starting Bearstorm Miner on pool: ${POOL}"

# Nice -n 15 ensures Home Assistant has priority over mining
nice -n 15 /usr/bin/xmrig --url "$POOL" --user "$USER" --pass "$PASS"
