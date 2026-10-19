# XMRig HAOS 2.0.0-beta.2 — Experimental Pre-release

**Status:** experimental beta for Home Assistant OS (amd64); **not** the stable HAOS Safe add-on.

This beta contains a standalone Python-controlled XMRig mining add-on with Home Assistant MQTT Discovery and unprivileged process/container monitoring. The stable `xmrig_haos` and legacy Supervised/MSR implementations are unchanged.

## Highlights

- **Mining ON/OFF MQTT switch:** starts/stops *only the XMRig miner process*, leaving the lightweight add-on controller running for MQTT connectivity, container resource monitoring and automation. The switch is deliberately independent of the Home Assistant add-on Start/Stop button.
- **Complete Home Assistant MQTT Discovery:** hashrates (10-second, 60-second, 15-minute), accepted and rejected shares, uptime, HTTP API available, pool connected, process CPU/RAM/peak/OS threads/CPU time, add-on CPU/RAM, network RX/TX, and disk read/write counters.
- **CPU normalized to Supervisor-style percentage:** 100% is all online logical CPUs; four fully occupied logical CPUs on a 12-logical-CPU host report ~33.33%, not ~400%.
- **Memory visibility:** XMRig RAM usage, peak RAM and **Add-on RAM usage in MiB** retained; obsolete **Add-on RAM usage percent** removed, including its MQTT retained Discovery registration.
- **Metrics while Mining OFF:** add-on CPU/RAM/network/disk metrics continue to publish, while XMRig-only metrics become unavailable.
- **State and crash guard:** a first-time miner starts OFF. User-requested ON/OFF state is persisted across graceful add-on restarts; following an unclean crash, a retained guard prevents automatic mining until a new explicit ON command. Watchdog restarting the add-on does not bypass this guard.
- **HAOS security model:** independent beta slug, manual boot, Protection Mode-compatible configuration, no host PID/network privileges, no MSR/kernel changes, no mining credentials in MQTT messages.

## Testing and verification

**Automated beta tests completed successfully:** GitHub Actions validation, standalone HAOS build, isolated Python controller and MQTT/broker/runtime checks, guard behavior, CPU normalization, Discovery and retained-entity cleanup. Documentation-only changes after the tested code are tracked on `develop-v2`.

**Live operator HAOS test completed for beta.2:** installed and updated as a separate local beta add-on, 4 mining threads, 12 logical CPUs. Measured Mining ON: add-on CPU **33.33%**, XMRig CPU **33.33%**, add-on memory **2365.46 MiB**, XMRig memory **2352.72 MiB**, 10-second hashrate **1732.22 H/s**, 60-second hashrate **1730.2 H/s**, **3 accepted / 0 rejected** shares. Mining OFF: add-on CPU **0.66%**, RAM **14.69 MiB**, XMRig process sensors unavailable while container sensors remained available. The 15-minute hashrate was not yet available after a ~140-second test.

**Scope limitation:** A deliberate hard-kill / sudden power-loss failure test was **not** run on production HAOS; crash-guard behavior was covered by isolated tests. Results from one HAOS system do not guarantee compatibility with every host, CPU, kernel or broker.

## ⚠ CPU Temperature, Cooling and User Responsibility

**You are responsible for determining and configuring appropriate CPU temperature limits for your specific processor, cooling system, enclosure and operating environment.** Consult the processor manufacturer's specifications and your hardware vendor's guidance; do not copy another user's temperature thresholds. A manufacturer's maximum junction temperature is **not** a recommended continuous operating temperature.

**Operating above normal, manufacturer-recommended sustained temperatures is strongly discouraged.** Set conservative warning and mining-shutdown thresholds based on your own hardware, monitor them continuously while mining, and ensure the shutdown mechanism actually works. This add-on does **not** automatically enforce hardware-specific temperature limits or provide built-in thermal shutdown through the MQTT Mining switch; use suitable independent hardware protection and, if desired, tested Home Assistant automations. Do not assume that a Home Assistant automation can replace CPU hardware protections.

**Use at your own risk.** The project author and contributors do not accept responsibility for overheating, equipment damage, instability, data loss or other consequences arising from incorrect configuration, inappropriate temperature limits, inadequate cooling or misuse, **to the extent permitted by applicable law**. This disclaimer does not override mandatory consumer rights or liability that cannot legally be excluded.

## Installation / migration

This release is an **experimental standalone beta** (slug `xmrig_haos_beta`). It is **not** a drop-in stable HAOS Safe update. Preserve a full Home Assistant backup and the previous local-beta source before applying beta changes. Use only the `xmrig_haos_beta/` directory with the documented beta installation/update procedure and confirm your wallet/pool settings after an update. Keep the stable add-on separate.

Read the complete [beta README](xmrig_haos_beta/README.md) for **every MQTT entity and topic**, Mining switch explanation, Watchdog/crash guard state handling, safe test procedure, limitations and rollback information. See the [repository README](README.md) for stable-vs-beta differences.

**Tag requested:** `v2.0.0-beta.2` against reviewed `develop-v2` documentation commit, **GitHub pre-release**, not a stable/latest production release.
