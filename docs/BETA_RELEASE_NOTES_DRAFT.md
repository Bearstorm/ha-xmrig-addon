# XMRig Miner 2.0 — Beta Release Notes (DRAFT / NOT PUBLISHED)

**Candidate version:** `2.0.0-beta.0`  
**Candidate add-on:** `xmrig_haos_beta` (amd64 only)  
**Status:** staging candidate; real HAOS acceptance still outstanding.

## What is implemented in the beta candidate

- Separate experimental HAOS add-on package; no replacement of the stable `xmrig_haos` package.
- XMRig 6.26.0 included and SHA-256 checked during the Docker build.
- Isolated Python process Controller with bounded restart attempts, SIGTERM shutdown handling and no dependency of mining lifecycle on MQTT.
- Optional Supervisor-discovered MQTT publisher and Home Assistant MQTT Discovery entities.
- MQTT Mining ON/OFF commands on the isolated `xmrig_haos_beta/command` topic; retained ON messages are rejected.
- Durable ON/OFF preference with first-install default OFF and crash guard to prevent unclean restart from auto-starting mining.
- Best-effort HTTP telemetry. If the HTTP API is unavailable, old hashrate metrics are not published as current readings.
- Experimental config is manual boot, no full host access, no host PID or host networking, and optional MQTT service access.

## What was tested in isolated CI

- Python unit and mock-child process lifecycle tests, including real Linux SIGTERM and SIGKILL scenarios.
- Real local loopback Mosquitto integration for beta MQTT namespace and retained Discovery.
- Strict beta source isolation, Docker build and offline import and entrypoint smoke tests.
- Fail-closed behavior for bad state, inaccessible local files and corrupted crash guard.
- Representative credential leak checks, static host privilege checks and checksums.

**Important:** these tests do not establish correct behavior in a real Home Assistant Supervisor.

## Known limits and prerequisites

- No real HAOS Supervisor installation has been accepted yet.
- Protection Mode ON, real Supervisor MQTT service, actual host process teardown and rollback are unverified.
- Base Bookworm container image and OS package dependencies are not all pinned by immutable digests; review before public release.
- No ARM image or guaranteed hashrate, energy consumption or temperature claim.
- A missing wallet is intentionally rejected at runtime. A test-only identifier can be supplied for OFF-state staging validation.
- MQTT unavailable means MQTT control is unavailable. MQTT disconnect does not automatically stop already running mining.
- The stable HAOS Safe add-on still uses `run.sh` and **does not** gain beta MQTT features until a separate approved stable release.

## Staging and rollback

Use the *source-only staging artifact* from a green `develop-v2` GitHub Actions run,
verify the SHA-256 and follow `docs/BETA_STAGING_HANDOFF.md`. Never run an
unaccepted candidate on the production Home Assistant.

## Publication decision

**BLOCKED:** Public beta tag, GitHub Release or GHCR beta image must wait for
documented staging acceptance and explicit approval. This is a release notes
draft, not a claim that a beta has been shipped.
