# XMRig Miner 2.0 — Experimental HAOS Beta

**Version 2.0.0-beta.2 — beta candidate, pending live acceptance for resource monitoring.**
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
- A controlled ON/OFF restart, real pool connection and accepted share were verified on the operator's actual HAOS using beta.0. The new beta.2 resource sensors still require live acceptance.
- Unexpected container termination was **not** reproduced on the operator's production HAOS. The guard was exercised by isolated tests only.

## Local beta test and rollback

1. Finish and verify a full HAOS backup. Keep stable `xmrig_haos` running independently, and record beta.0 files/settings before replacing any local beta sources.
2. With Mining OFF, stop the existing local beta add-on. Stage only the reviewed `xmrig_haos_beta/` source from the exact tested beta.2 commit. Do **not** copy the entire repository into `/addons/local`.
3. Confirm the `xmrig_haos_beta` slug, version, Protection Mode, manual boot and minimal permissions. Rebuild/install the local beta through the supported HAOS UI.
4. Start beta.2 with Mining OFF. Verify all container resource sensors are available where supported, and XMRig-specific sensors remain unavailable until Mining ON.
5. With operator consent, conduct a short bounded test with a known pool and wallet, monitor CPU/RAM and share acceptance, then return Mining OFF.
6. If any regression occurs, turn Mining OFF, stop beta.2, restore the saved beta.0 local source and rebuild it; restore the full HAOS backup if required. Stable `xmrig_haos` must remain untouched.

The local HAOS package does not publish an image to GHCR. GitHub Actions builds a standalone candidate and uploads short-lived source artifacts; an artifact is **not** a public GitHub Release.

## Release gate

Do not publish a public beta.2 release until isolated CI tests pass and live HAOS acceptance confirms resource monitoring and rollback. Never claim that CI alone proves live HAOS behavior.
