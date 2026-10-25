# 🪙 XMRig Miner 2.0 — All-in-One Beta 3

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
![Architecture](https://img.shields.io/badge/Arch-amd64-orange.svg)
![HAOS Compatible](https://img.shields.io/badge/HAOS-Compatible-green.svg)
![Supervised MSR](https://img.shields.io/badge/Supervised-Debian%2012-blue.svg)
![MSR Optional](https://img.shields.io/badge/MSR-Optional-yellow.svg)
![RandomX Optimized](https://img.shields.io/badge/RandomX-Optimized-red.svg)

![Build](https://github.com/Bearstorm/ha-xmrig-addon/actions/workflows/publish.yml/badge.svg)
![GHCR](https://img.shields.io/badge/GHCR-Published-blue)

![Release](https://img.shields.io/github/v/release/Bearstorm/ha-xmrig-addon?display_name=tag&style=flat-square)
![License](https://img.shields.io/github/license/Bearstorm/ha-xmrig-addon)
![Visitors](https://komarev.com/ghpvc/?username=Bearstorm&repo=ha-xmrig-addon&style=flat-square)

One Home Assistant OS amd64 add-on combining XMRig 6.26.0, Python controller, MQTT Discovery, Mining ON/OFF switch, miner and resource telemetry, automatic/manual startup, and fail-closed CPU temperature protection.

## Installation
Install the xmrig_haos_beta add-on from repository branch feature/beta-integrated-thermal-protection. This is an experimental pre-release separate from stable HAOS Safe. Configure wallet, pool and worker before starting; wallet is blank by default. Do not run Beta.2 and All-in-One concurrently because their MQTT identities overlap.

## Startup and MQTT
Automatic (default): mining starts on each normal add-on startup, even after a previous MQTT OFF. Manual: mining stays OFF until the Home Assistant MQTT Discovery **Mining** switch is turned ON (or an equivalent MQTT ON command is sent). MQTT OFF stops the miner but leaves controller and resource monitoring running. Switching startup modes requires an add-on restart.

## Thermal protection
Disabled by default. To enable, set thermal_protection_enabled, a valid HA CPU temperature sensor entity reporting Celsius, thermal_limit (40–105), thermal_sensor_timeout (60–3600), and thermal_notifications. Too-hot, missing, invalid or stale readings stop mining and latch OFF. A recorded thermal trip or unclean shutdown blocks automatic restart. To resume after a thermal trip, check that the sensor has cooled, then turn ON the **Mining** switch in Home Assistant (under the XMRig Miner 2.0 All-in-One Beta MQTT device). This switch sends MQTT ON for you; manual MQTT publishing is not required. The controller rechecks the current temperature before clearing the thermal latch. If the sensor is unsafe or unavailable, mining remains OFF. The HA add-on Start/Stop buttons control the add-on container, not the miner inside it; restarting the add-on alone must never clear a thermal trip.

## Safety and release status
No privileged host access, host network/PID or MSR. Mining consumes CPU and electricity. Beta.3 combines the live-HAOS-tested Thermal Test .6 behavior with Beta.2 monitoring. Fresh integrated add-on testing and GitHub CI must pass before publication. Stable main and legacy Supervised remain untouched.

---

## 💝 Free, Non-Commercial Project and Voluntary Donations

This add-on is developed and shared **free of charge as a personal, non-commercial open-source project** under the MIT License. There is **no purchase price, subscription, or mandatory donation** to download, install, use, or update it.

The **Support me** PayPal link below is entirely optional. Contributions are voluntary expressions of appreciation; they are **not a required payment for the software**, do not purchase technical support or a service contract, and do not create any additional warranty. The author makes no promise of paid support, updates, or particular results in exchange for donations.

Users are responsible for deciding whether mining is appropriate for their own hardware, setting safe CPU loads and processor-specific temperature limits, providing adequate cooling, and monitoring their systems. Mining should not exceed the manufacturer's recommended sustained operating conditions.

The software is provided **"AS IS", without warranty of any kind**, under the terms of the MIT License and subject to applicable law. The project author and contributors disclaim liability to the extent permitted by law; no disclaimer excludes liability that cannot legally be excluded.

---

## Support me 🔥
- 😄 PayPal one-off donation
<a href="https://www.paypal.com/donate/?hosted_button_id=PVATF8G5NZ392">
  <img src="https://raw.githubusercontent.com/andreostrovsky/donate-with-paypal/925c5a9e397363c6f7a477973fdeed485df5fdd9/blue.svg" alt="Donate with PayPal" height="40"/>
