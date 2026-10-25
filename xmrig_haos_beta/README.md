# XMRig Miner 2.0 — All-in-One Beta 3

One Home Assistant OS amd64 add-on combining XMRig 6.26.0, Python controller, MQTT Discovery, Mining ON/OFF switch, miner and resource telemetry, automatic/manual startup, and fail-closed CPU temperature protection.

## Installation
Install the xmrig_haos_beta add-on from repository branch feature/beta-integrated-thermal-protection. This is an experimental pre-release separate from stable HAOS Safe. Configure wallet, pool and worker before starting; wallet is blank by default. Do not run Beta.2 and All-in-One concurrently because their MQTT identities overlap.

## Startup and MQTT
Automatic (default): mining starts on each normal add-on startup, even after a previous MQTT OFF. Manual: mining stays OFF until MQTT ON. MQTT OFF stops the miner but leaves controller and resource monitoring running. Switching startup modes requires an add-on restart.

## Thermal protection
Disabled by default. To enable, set thermal_protection_enabled, a valid HA CPU temperature sensor entity reporting Celsius, thermal_limit (40–105), thermal_sensor_timeout (60–3600), and thermal_notifications. Too-hot, missing, invalid or stale readings stop mining and latch OFF. A recorded thermal trip or unclean shutdown blocks automatic restart. To resume after a thermal trip, check the sensor and send a deliberate MQTT ON; the controller verifies current temperature first.

## Safety and release status
No privileged host access, host network/PID or MSR. Mining consumes CPU and electricity. Beta.3 combines the live-HAOS-tested Thermal Test .6 behavior with Beta.2 monitoring. Fresh integrated add-on testing and GitHub CI must pass before publication. Stable main and legacy Supervised remain untouched.