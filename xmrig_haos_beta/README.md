# XMRig Miner 2.0 — Experimental HAOS Beta

**Version 2.0.0-beta.2 — experimental pre-release; CPU, RAM and MQTT functions verified on one real HAOS installation.**
This is a separate local Home Assistant add-on, not the stable HAOS Safe release.
The existing `xmrig_haos` Dockerfile, slug, image and `/run.sh` remain unchanged.

## Features

- Standalone slug `xmrig_haos_beta`, boot `manual`, stage `experimental`, Protection Mode compatible.
- Python controller with MQTT Discovery, ON/OFF switch, HTTP miner telemetry, persistent mining preference and unclean-shutdown startup guard.
- First-ever start defaults to Mining OFF; MQTT ON requires an explicit user command.
- Miner telemetry: hashrate (10 s, 60 s, 15 m), accepted/rejected shares, uptime, pool connection and HTTP API availability.
- Resource telemetry every ~5 seconds from unprivileged Linux interfaces:
  - XMRig process: CPU usage (% of all online logical CPUs, matching Supervisor), resident RAM (MiB), recorded peak RSS (MiB), operating-system thread count, accumulated CPU seconds.
  - Entire add-on container: CPU usage (% of all online logical CPUs), cgroup RAM (MiB), received/sent network traffic and cgroup disk read/write bytes (reported in MiB).
- All resource metrics are best-effort. A missing or unsupported kernel/cgroup statistic produces an unavailable value, **not an invented zero**.
- Container metrics continue publishing while Mining is OFF. Process metrics are unavailable while XMRig is stopped.
- Unchanged beta MQTT identity `xmrig_haos_beta` and existing entity unique IDs. New entities are created separately within the same HA device.
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

- Home Assistant OS (amd64), standalone slug `xmrig_haos_beta`, `boot: manual`, `stage: experimental`.
- Unprivileged Python controller supervises the XMRig process; no MSR or host kernel modifications.
- XMRig mining settings: `pool`, `port`, `wallet`, `worker`, `threads`, `priority`, `tls_mode` (`auto`, `enabled`, `disabled`). Wallet must be configured by the user.
- Optional Supervisor-provided MQTT broker service (`mqtt:want`): MQTT Discovery, telemetry, binary status indicators and Mining switch. MQTT failure must not stop an already running miner.
- Resource monitoring samples available process and cgroup v2 statistics approximately every **5 seconds**, without privileged access.
- No `host_network`, `host_pid`, or `full_access`. HAOS Protection Mode remains compatible; no new monitoring dependency.
- No wallet or pool credentials are included in published MQTT telemetry.

## MQTT integration — complete entity list

After the add-on starts and connects to an available MQTT broker, Home Assistant's MQTT integration discovers a device named **XMRig Miner 2.0**. This beta uses the `xmrig_haos_beta` topic namespace and has unique IDs independent of the stable add-on.

### Control (1 switch)

| Entity | Meaning |
| --- | --- |
| **Mining** | **ON** starts the XMRig mining process; **OFF** stops only that process while leaving the add-on, MQTT connectivity and container monitoring running |

The switch command topic is `xmrig_haos_beta/command` with `ON` / `OFF` payloads; retained/stale commands are not treated as fresh user actions. Its state reflects the running process, not merely the last command. State updates and connection interruptions can briefly show unavailable status.

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
| `xmrig_haos_beta/command` | MQTT Mining ON/OFF command |
| `xmrig_haos_beta/telemetry` | XMRig metrics / binary status |
| `xmrig_haos_beta/resources` | CPU, RAM, network, disk resource JSON |
| `xmrig_haos_beta/mqtt_availability` | Controller MQTT connection availability |
| `xmrig_haos_beta/process_availability` | Child XMRig process availability / Mining switch state |
| `xmrig_haos_beta/api_availability` | XMRig API-dependent telemetry availability |
| `homeassistant/.../xmrig_haos_beta/.../config` | Home Assistant MQTT Discovery configuration |

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

## Local installation and rollback

This experimental beta is developed separately from the stable add-on. **Do not overwrite the existing stable `xmrig_haos` folder, image, or configuration.** Its public repository installation flow may differ from manually installing the standalone local-beta folder.

1. Create and verify a full Home Assistant backup. Preserve any earlier local-beta source/configuration before an update.
2. Obtain the reviewed `xmrig_haos_beta/` directory from the appropriate beta.2 source/tag and place **only that directory** in your Home Assistant local add-ons directory, as supported by your HAOS setup.
3. Confirm `slug: xmrig_haos_beta`, version `2.0.0-beta.2`, manual boot, the expected minimal permissions and your intended wallet/pool.
4. Refresh the local add-on store and install/update the **Beta Test** add-on; keep HAOS Protection Mode enabled.
5. Start the add-on with Mining OFF. Verify MQTT Discovery, persistent container resource values and unavailable process metrics.
6. If you deliberately enable Mining, monitor cooling, Home Assistant responsiveness, CPU/RAM and pool acceptance. Return Mining OFF after your test.
7. If problems arise, switch Mining OFF, stop beta, restore the backed-up local-beta source and rebuild/reinstall it; use the full HA backup if needed. Stable `xmrig_haos` remains independent.

For users already on an earlier beta, update the beta add-on through Home Assistant after replacing the local-beta source. Do not delete its stored configuration.

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

## Support me 🔥
- 😄 PayPal one-off donation
<a href="https://www.paypal.com/donate/?hosted_button_id=PVATF8G5NZ392">
  <img src="https://raw.githubusercontent.com/andreostrovsky/donate-with-paypal/925c5a9e397363c6f7a477973fdeed485df5fdd9/blue.svg" alt="Donate with PayPal" height="40"/>
</a>
