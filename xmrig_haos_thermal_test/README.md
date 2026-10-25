# XMRig Miner 2.0 — Experimental HAOS Beta

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
![Architecture](https://img.shields.io/badge/Arch-amd64-orange.svg)
![HAOS](https://img.shields.io/badge/HAOS-Tested%20on%20one%20host-green.svg)
![Beta](https://img.shields.io/badge/Release-2.0.0--beta.2%20candidate-orange.svg)
![MQTT](https://img.shields.io/badge/MQTT-Discovery%20%2B%20ON%2FOFF-blue.svg)
![Protection](https://img.shields.io/badge/Protection%20Mode-Compatible-green.svg)

[![Runtime tests](https://github.com/Bearstorm/ha-xmrig-addon/actions/workflows/runtime-test.yml/badge.svg?branch=develop-v2)](https://github.com/Bearstorm/ha-xmrig-addon/actions/workflows/runtime-test.yml)
![CI](https://img.shields.io/badge/Beta%20CI-Tested-green.svg)
![License](https://img.shields.io/github/license/Bearstorm/ha-xmrig-addon)
[![Visitors](https://hits.sh/github.com/Bearstorm/ha-xmrig-addon.svg?label=Visitors&style=flat-square)](https://hits.sh/github.com/Bearstorm/ha-xmrig-addon/)

**Badge scope:** these badges describe the separate **experimental beta**. They do not claim a published GitHub pre-release or GHCR beta image. The stable release badge in the [repository README](../README.md) refers to repository tags and should not be interpreted as a beta.2 release.

**Version 2.0.0-beta.2 — experimental pre-release; CPU, RAM and MQTT functions verified on one real HAOS installation.**
This is a separate local Home Assistant add-on, not the stable HAOS Safe release.
The existing `xmrig_haos` Dockerfile, slug, image and `/run.sh` remain unchanged.

## Features

- Standalone slug `xmrig_haos_thermal_test`, boot `manual`, stage `experimental`, Protection Mode compatible.
- Python controller with MQTT Discovery, ON/OFF switch, HTTP miner telemetry, persistent mining preference and unclean-shutdown startup guard.
- First-ever start defaults to Mining OFF; MQTT ON requires an explicit user command.
- Miner telemetry: hashrate (10 s, 60 s, 15 m), accepted/rejected shares, uptime, pool connection and HTTP API availability.
- Resource telemetry every ~5 seconds from unprivileged Linux interfaces:
  - XMRig process: CPU usage (% of all online logical CPUs, matching Supervisor), resident RAM (MiB), recorded peak RSS (MiB), operating-system thread count, accumulated CPU seconds.
  - Entire add-on container: CPU usage (% of all online logical CPUs), cgroup RAM (MiB), received/sent network traffic and cgroup disk read/write bytes (reported in MiB).
- All resource metrics are best-effort. A missing or unsupported kernel/cgroup statistic produces an unavailable value, **not an invented zero**.
- Container metrics continue publishing while Mining is OFF. Process metrics are unavailable while XMRig is stopped.
- Unchanged beta MQTT identity `xmrig_haos_thermal_test` and existing entity unique IDs. New entities are created separately within the same HA device.
- No new host privileges, no host networking, no host PID namespace, no `full_access`, no miner credentials in telemetry, and no third-party monitoring dependency.

## Important limitations

- The unreliable add-on RAM percentage entity was removed from MQTT Discovery; its retained MQTT configuration is explicitly cleared on broker connection. Add-on RAM in MiB remains available. Container network stats come from the container network namespace.
- CPU percentages are sampled over intervals and divided by the number of available logical CPUs; the first reading is unavailable. Four saturated cores on a 12-thread host represent about 33.3%, matching Supervisor conventions. XMRig's RSS is not equivalent to total RandomX memory charge.
- The operating-system thread count is **not** the count of configured mining workers.
- Disk statistics reflect cgroup I/O accounting when available. Values may differ from the Supervisor's presentation or host aggregate.
- Hardware CPU temperature and electrical power use are not provided without trusted device sensors.
- Controlled Mining ON/OFF, real pool connection, accepted shares and beta.2 resource sensors were verified on one real HAOS installation. This does not guarantee compatibility on other systems.
- Unexpected container termination was **not** reproduced on the operator's production HAOS. The guard was exercised by isolated tests only.

## Why there are two ON/OFF controls

**Starting or stopping the Home Assistant add-on is different from starting or stopping mining.**

| Action | Python controller / MQTT | XMRig mining process | MQTT metrics |
| --- | --- | --- | --- |
| Add-on START, Mining OFF | Running | Stopped | Add-on/container metrics remain available; miner metrics unavailable |
| Add-on START, Mining ON | Running | Running | Both container and miner metrics available |
| Add-on STOP | Stopped | Stopped | Device becomes unavailable |

The MQTT **Mining** switch controls **only the XMRig child process**, not the add-on container. Keeping the lightweight controller online while mining is OFF means that Home Assistant can still monitor the add-on and start mining later without rebuilding or restarting the add-on. This also permits HA automations based on electricity, CPU load, temperatures or other conditions. The switch is deliberate, not a duplicate add-on power switch.

The actual idle memory use observed in one HAOS test was approximately **14.69 MiB**; usage varies by host. The MQTT switch does **not** change Home Assistant's `Start on boot` or `Watchdog` settings.

### Mining state, restarts and safety guard

- On a **fresh installation**, Mining starts **OFF**. Turn it ON explicitly via the MQTT switch.
- The controller **persists the requested Mining ON/OFF preference** across *graceful* add-on stops and starts. A previously enabled miner can therefore start automatically again after a clean controller restart, provided that the add-on itself starts and the stored state is intact.
- After an **unexpected/unclean termination**, a startup guard prevents automatic mining; Mining stays OFF until explicitly enabled again.
- If the stored state cannot be read safely, mining defaults to OFF.
- A stopped add-on is not remotely controllable via its MQTT Mining switch; start the add-on first.
- The unclean-shutdown guard has been exercised by isolated tests but **has not been deliberately tested by crashing the operator's production HAOS**.

If you prefer mining to remain OFF after *every* HAOS reboot, that is **not** a beta.2 guarantee: turn Mining OFF before stopping/rebooting, or enforce your preferred policy with an appropriate Home Assistant automation. Do not rely on a crash guard to replace deliberate OFF control.

## Features and configuration

- Home Assistant OS (amd64), standalone slug `xmrig_haos_thermal_test`, `boot: manual`, `stage: experimental`.
- Unprivileged Python controller supervises the XMRig process; no MSR or host kernel modifications.
- XMRig mining settings: `pool`, `port`, `wallet`, `worker`, `threads`, `priority`, `tls_mode` (`auto`, `enabled`, `disabled`). Wallet must be configured by the user.
- Optional Supervisor-provided MQTT broker service (`mqtt:want`): MQTT Discovery, telemetry, binary status indicators and Mining switch. MQTT failure must not stop an already running miner.
- Resource monitoring samples available process and cgroup v2 statistics approximately every **5 seconds**, without privileged access.
- No `host_network`, `host_pid`, or `full_access`. HAOS Protection Mode remains compatible; no new monitoring dependency.
- No wallet or pool credentials are included in published MQTT telemetry.

## MQTT integration — complete entity list

After the add-on starts and connects to an available MQTT broker, Home Assistant's MQTT integration discovers a device named **XMRig Miner 2.0**. This beta uses the `xmrig_haos_thermal_test` topic namespace and has unique IDs independent of the stable add-on.

### Control (1 switch)

| Entity | Meaning |
| --- | --- |
| **Mining** | **ON** starts the XMRig mining process; **OFF** stops only that process while leaving the add-on, MQTT connectivity and container monitoring running |

The switch command topic is `xmrig_haos_thermal_test/command` with `ON` / `OFF` payloads; retained/stale commands are not treated as fresh user actions. Its state reflects the running process, not merely the last command. State updates and connection interruptions can briefly show unavailable status.

### Mining telemetry (6 sensors)

| Entity | Unit | Description |
| --- | --- | --- |
| Hashrate 10s | H/s | Approximate 10-second mining hashrate |
| Hashrate 60s | H/s | Approximate 60-second mining hashrate |
| Hashrate 15m | H/s | Approximate 15-minute mining hashrate |
| Accepted shares | count | Shares accepted by the pool |
| Rejected shares | count | Shares rejected by the pool |
| Uptime | s | Reported XMRig running time |

Hashrate windows are available only after enough runtime/sample data. When Mining is OFF or the XMRig HTTP API is unavailable, miner telemetry is unavailable rather than reporting stale values.

### Binary status (2 entities)

| Entity | Meaning |
| --- | --- |
| HTTP API available | Whether the running XMRig process is currently responding to its local monitoring API |
| Pool connected | Whether XMRig reports a pool connection |

When Mining is OFF, these statuses become unavailable rather than falsely implying an active miner.

### XMRig process resources (5 sensors)

| Entity | Unit | Description |
| --- | --- | --- |
| XMRig CPU usage | % | Process CPU as a share of **all available logical CPUs**, using the same normalization style as HA Supervisor |
| XMRig RAM usage | MiB | Current resident memory (RSS) of the XMRig process |
| XMRig RAM peak | MiB | Peak resident memory recorded by the OS |
| XMRig OS threads | count | All OS threads in the process, **not** the configured mining-worker thread count |
| XMRig CPU time | s | Accumulated XMRig CPU execution time |

These five values become unavailable when the mining process is stopped.

### Entire add-on resources (6 sensors)

| Entity | Unit | Description |
| --- | --- | --- |
| Add-on CPU usage | % | Container CPU as a share of **all available logical CPUs**, comparable to HA Supervisor |
| Add-on RAM usage | MiB | Current memory charged to the add-on cgroup |
| Add-on network received | MiB | Cumulative received traffic from the container network namespace |
| Add-on network sent | MiB | Cumulative sent traffic from the container network namespace |
| Add-on disk read | MiB | Cumulative cgroup read bytes where available |
| Add-on disk written | MiB | Cumulative cgroup written bytes where available |

These six values continue to publish even when **Mining is OFF**, as long as the add-on/controller is running. Unavailable OS/cgroup statistics are reported as unknown, not fabricated zeroes. Disk/network counters are cumulative for the corresponding resource accounting lifetime, not instantaneous bandwidth.

**CPU percentage example:** four fully loaded logical CPUs on a host with 12 logical CPUs display approximately **33.33%**, not 400%. Both XMRig and add-on CPU percentages use this convention. This is not the percentage of *configured mining threads*. Actual CPU utilization can vary.

**Removed entity:** the unreliable **Add-on RAM usage percent** sensor has been removed in beta.2. Its retained MQTT Discovery registration is cleaned up automatically on broker connection. **Add-on RAM usage in MiB remains supported.**

### MQTT topics

| Topic | Purpose |
| --- | --- |
| `xmrig_haos_thermal_test/command` | MQTT Mining ON/OFF command |
| `xmrig_haos_thermal_test/telemetry` | XMRig metrics / binary status |
| `xmrig_haos_thermal_test/resources` | CPU, RAM, network, disk resource JSON |
| `xmrig_haos_thermal_test/mqtt_availability` | Controller MQTT connection availability |
| `xmrig_haos_thermal_test/process_availability` | Child XMRig process availability / Mining switch state |
| `xmrig_haos_thermal_test/api_availability` | XMRig API-dependent telemetry availability |
| `homeassistant/.../xmrig_haos_thermal_test/.../config` | Home Assistant MQTT Discovery configuration |

The add-on does not include an MQTT broker. Configure the existing Home Assistant MQTT integration and broker; ensure MQTT is reachable and the beta add-on receives broker connection information.

## Real HAOS acceptance results

Verified on an operator's Home Assistant OS installation, with **4 mining threads and 12 online logical CPUs**. These are **observations on one host, not performance guarantees**:

| Metric | Mining ON (about 140s) | Mining OFF |
| --- | --- | --- |
| Add-on CPU | 33.33% | 0.66% |
| XMRig CPU | 33.33% | Unavailable |
| Add-on RAM | 2365.46 MiB | 14.69 MiB |
| XMRig RAM RSS | 2352.72 MiB | Unavailable |
| Hashrate 10s | 1732.22 H/s | Unavailable |
| Hashrate 60s | 1730.2 H/s | Unavailable |
| Accepted / rejected shares | 3 / 0 | Unavailable |

The pool connection, process ON/OFF, MQTT Discovery, resource sensors and retained-entity cleanup were observed working. The 15-minute hashrate was naturally unavailable during the 140-second test.

Additional isolated GitHub Actions validation and runtime checks passed for the beta.2 candidate. No deliberate unexpected hard-crash test was performed on production HAOS.

## Install from the GitHub beta repository (HAOS app store)

Home Assistant can install this beta from a **custom app/add-on repository**. It does **not** appear automatically in every user's store, and this branch is not the default stable channel.

**Beta repository URL:** `https://github.com/Bearstorm/ha-xmrig-addon#develop-v2`

[![Add the XMRig beta repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBearstorm%2Fha-xmrig-addon%23develop-v2)

1. Make a full Home Assistant backup and keep your existing stable add-on unchanged.
2. In Home Assistant OS, open **Settings → Apps → Install app → ⋮ → Repositories** (older versions may say **Add-ons**).
3. Add the beta repository URL above, **including `#develop-v2`**. Wait for the repository to load/refresh.
4. Choose **XMRig Miner 2.0 (Beta Test)**, verify its experimental status, then install it. Check Protection Mode is enabled, configure your pool/wallet and keep Mining OFF initially.
5. If MQTT is configured, verify the discovered Mining switch and resource sensors before deliberately enabling mining.

**Important:** The GitHub repository installation is not the same Supervisor add-on identity as a local copy in `/addons/local/xmrig_haos_thermal_test`. If you have already installed the local beta, **do not run both copies together**: their MQTT discovery identifiers and `xmrig_haos_thermal_test/*` topics overlap. Back up settings, stop Mining and the local beta, and plan a controlled migration before starting the repository-installed beta. Do not delete or overwrite stable add-ons.

The default GitHub repository URL **without** `#develop-v2` follows the `main` branch and does not currently contain this beta. GitHub Releases alone do not make a new version appear in Home Assistant; the app store reads repository files and the version in `config.yaml`. Users must first add the custom repository; new versions then become available as app updates after the repository refreshes. Updates are **not automatically installed** merely because a GitHub release or commit exists.

For official repository behavior, see [Home Assistant: Create and share a repository](https://contributors.home-assistant.io/apps/guides/repository/).

## Local installation and rollback

This experimental beta is developed separately from the stable add-on. **Do not overwrite the existing stable `xmrig_haos` folder, image, or configuration.** Its public repository installation flow may differ from manually installing the standalone local-beta folder.

1. Create and verify a full Home Assistant backup. Preserve any earlier local-beta source/configuration before an update.
2. Obtain the reviewed `xmrig_haos_thermal_test/` directory from the appropriate beta.2 source/tag and place **only that directory** in your Home Assistant local add-ons directory, as supported by your HAOS setup.
3. Confirm `slug: xmrig_haos_thermal_test`, version `2.0.0-beta.2`, manual boot, the expected minimal permissions and your intended wallet/pool.
4. Refresh the local add-on store and install/update the **Beta Test** add-on; keep HAOS Protection Mode enabled.
5. Start the add-on with Mining OFF. Verify MQTT Discovery, persistent container resource values and unavailable process metrics.
6. If you deliberately enable Mining, monitor cooling, Home Assistant responsiveness, CPU/RAM and pool acceptance. Return Mining OFF after your test.
7. If problems arise, switch Mining OFF, stop beta, restore the backed-up local-beta source and rebuild/reinstall it; use the full HA backup if needed. Stable `xmrig_haos` remains independent.

For users already on an earlier beta, update the beta add-on through Home Assistant after replacing the local-beta source. Do not delete its stored configuration.

## ⚠ CPU Temperature, Cooling and User Responsibility

**You are responsible for determining and configuring appropriate CPU temperature limits for your specific processor, cooling system, enclosure and operating environment.** Consult the processor manufacturer's specifications and your hardware vendor's guidance; do not copy another user's temperature thresholds. A manufacturer's maximum junction temperature is **not** a recommended continuous operating temperature.

**Operating above normal, manufacturer-recommended sustained temperatures is strongly discouraged.** Set conservative warning and mining-shutdown thresholds based on your own hardware, monitor them continuously while mining, and ensure the shutdown mechanism actually works. This add-on does **not** automatically enforce hardware-specific temperature limits or provide built-in thermal shutdown through the MQTT Mining switch; use suitable independent hardware protection and, if desired, tested Home Assistant automations. Do not assume that a Home Assistant automation can replace CPU hardware protections.

**Use at your own risk.** The project author and contributors do not accept responsibility for overheating, equipment damage, instability, data loss or other consequences arising from incorrect configuration, inappropriate temperature limits, inadequate cooling or misuse, **to the extent permitted by applicable law**. This disclaimer does not override mandatory consumer rights or liability that cannot legally be excluded.

## Limitations and security

- **Experimental pre-release:** not a replacement for the stable HAOS Safe add-on; no guarantee for all hardware, kernels, brokers or HAOS installations.
- Only **amd64** is supported; no ARM builds in this beta.
- Unprivileged `/proc` and cgroup values vary by kernel and isolation configuration. Resource sampling may briefly show unknown on initial startup or during PID transitions.
- Add-on RAM and process RSS represent different accounting methods; neither is an exact electrical power consumption measurement.
- No CPU temperature or power sensor is manufactured: obtain these from suitable Home Assistant hardware/host integrations if needed.
- Mining can consume substantial CPU, memory and electricity and may interfere with critical Home Assistant services. Use a conservative thread count and monitor temperatures.
- **Start on boot is controlled by Home Assistant, not by the MQTT Mining switch.** The beta add-on ships with `boot: manual`.
- Protection Mode and host isolation must remain intact. Do not grant privileges or weaken Supervisor health to enable MSR.
- Legacy Home Assistant Supervised/MSR support in this repository does not imply that Supervised remains an officially supported HA installation method.

---

## 📄 License

This project is licensed under the MIT License.  
See the [LICENSE](../LICENSE) file for details.

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
</a>


## Integrated thermal protection (experimental development branch only)

The add-on Configuration panel includes optional, default-OFF thermal protection. Users select an existing Home Assistant temperature entity and set the limit (80 °C example), report timeout (180 seconds example) and notifications. No separate Blueprint or HA automation is required. The controller checks every 30 seconds and before Mining ON. Unsafe temperatures, missing/stale sensor reports, and API errors fail closed and latch mining OFF until add-on restart. Notifications are best-effort English persistent notifications. No host privileges or direct host thermal access are required; Supervisor Core API access is requested via homeassistant_api.

**Important:** the Core states API may omit last_reported even if HA templates expose it. This implementation intentionally blocks mining when that field is missing. Verify API compatibility and actual behavior on HAOS before merging or publishing. This is not a substitute for hardware thermal safeguards. The published beta.2 is unchanged.


## Installing the independent thermal test

Add a second custom add-on repository URL ending in `#feature/beta-integrated-thermal-protection` (or change the existing repo source only if you accept that it exposes development updates). Refresh the add-on store and select **XMRig Miner 2.0 (Thermal Test)**, slug `xmrig_haos_thermal_test`. It has independent data, options, MQTT discovery IDs, and MQTT command topics; do not run both mining instances concurrently. Keep the published Beta.2 untouched. Set a valid wallet, enable protection and set an existing temperature entity. If the Core API omits `last_reported`, mining will be blocked intentionally. This is a test candidate, not a public release.


### Mining start mode (Thermal Test .2)

`mining_start_mode` defaults to `automatic` for **new installs**: on first add-on start, mining begins only after the existing thermal safety check passes. `manual` starts the controller and MQTT monitoring but does not start mining until the MQTT Mining switch is turned ON. The mode is selected in the add-on Configuration; save and restart the add-on to apply it. The MQTT Mining switch continues to provide runtime ON/OFF control. An existing saved OFF state, including a thermal trip, always wins over `automatic`; changing the mode does **not** reset a safety latch or force mining back ON. An unexpected shutdown guard also blocks automatic restart. This is a first-start preference, not a second live Start button.


### Manual mode fix (.3)

`manual` now **always starts with Mining OFF**, even when the previous session saved Mining ON. The saved preference is reset to OFF on manual startup. Use the MQTT Mining switch to start mining after the add-on starts. `automatic` resumes a previously saved ON preference or starts on a clean first install; a saved OFF preference and crash guard still block automatic mining. Thermal protection remains authoritative in both modes.


### Manual → automatic transition (.4)

An explicit manual session can transition back to automatic startup on the next add-on restart. A separate persistent thermal safety marker blocks automatic restart after a thermal trip, even when the sensor later cools. A previously saved OFF state with no recorded manual transition remains OFF (including older installs); users can explicitly enable mining via MQTT once to establish a new ON preference. The configuration mode takes effect after saving and restarting the add-on. The safety latch is not reset merely by changing modes.
