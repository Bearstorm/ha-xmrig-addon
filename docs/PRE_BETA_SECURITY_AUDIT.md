# XMRig Miner 2.0 — pre-beta security audit

Date: 2026-10-13. Scope: development branch `develop-v2`; HAOS Safe add-on and isolated Python candidate.

**Status: NOT RELEASE READY.** This review is a code audit and CI test review, not an on-device penetration test or production validation.

## Verified properties

- The shipped `xmrig_haos/Dockerfile` still starts `/bin/bash /run.sh`. The Python Controller and MQTT switch are **not deployed** by that image.
- The test candidate `tests/runtime/Dockerfile.haos-python` contains the Python Controller and pinned `paho-mqtt==2.1.0`, but is not published.
- HAOS add-on configuration has `full_access: false`, `host_network: false`, `host_pid: false` and `apparmor: true`. These declarations alone do not replace an actual HAOS Protection Mode test.
- Release publishing must require an explicit verified `v2.*` tag at the current `main` HEAD. A push to `main` is build-only in the proposed development policy.
- MQTT commands are exact `ON`/`OFF`, are non-retained, and reach the miner only through the Controller event loop. MQTT callbacks do not directly create or kill the mining process.
- The MQTT LWT uses `mqtt_availability` rather than `process_availability`. The latter represents the mining process and must not be changed merely because a broker disconnected.
- The XMRig archive download has a pinned SHA-256 checksum; dependencies and base image are **not** all locked to immutable digests.

## Blocking items before beta

1. **Desired mining state persistence:** MQTT `OFF` currently stops XMRig only until the add-on restarts; the current Controller calls `manager.start()` at startup. Decide and test persistent `OFF` or explicitly document a restart-always-mines policy. Do not claim the switch remembers `OFF`.
2. **Controller lifecycle:** Test stop/start after retries are exhausted; verify a user stop never triggers automatic crash recovery; test SIGTERM and child reap with commands in flight.
3. **Real HAOS:** Test on a disposable/non-production HAOS instance with Protection Mode ON and the real Supervisor MQTT service; confirm startup, stop, restart, no excessive CPU/memory/thermal impact and graceful rollback to the existing `run.sh`.
4. **MQTT access control:** MQTT topic commands trust broker authentication and ACLs. Document that only authorized Home Assistant users/clients may publish to `xmrig_haos/command`; the MQTT payload alone is **not** an authorization layer.
5. **Container security and supply chain:** Pin or document base-image digest and Python dependency provenance; review outbound-only network needs, unprivileged runtime UID feasibility, Linux capabilities, and the minimum Supervisor API permission.
6. **Release procedure:** Verify branch/tag protection and required CI checks in GitHub repository settings. Main branch changes now build only; publishing requires an explicit release tag following a separate approval.

## Safe release sequence

1. Keep previous HAOS image and configuration as rollback target; back up Home Assistant.
2. Pass unit tests, real-Mosquitto integration tests, Docker mock-child runtime tests, and release-policy tests.
3. Run the Python candidate on isolated HAOS before modifying the production entrypoint.
4. Complete manual checks and resolve blockers; review PR before merge.
5. Merge to `main` only after approval, then create a verified `v2.*` release tag **only** after separate publication approval.
6. For any failure, stop the candidate and restore the existing `run.sh` version; check Supervisor health and MQTT retained Discovery entities.

This document does not authorize a merge, release, GHCR push, or installation into the user's live Home Assistant.
