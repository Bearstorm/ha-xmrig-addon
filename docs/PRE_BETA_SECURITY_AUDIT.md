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

1. **Desired mining state persistence — implemented in test candidate:** `mining_state.py` stores `ON/OFF` atomically in `/data/xmrig_state.json`; initial missing state keeps the legacy auto-start behavior, saved `OFF` blocks startup, and malformed state starts safely OFF. Unit-tested; still requires a real HAOS restart/rollback test. If persistence fails while stopping, the miner stops but an earlier ON state could remain on disk; monitor and report this before release.
2. **Controller lifecycle:** Test stop/start after retries are exhausted; verify a user stop never triggers automatic crash recovery; test SIGTERM and child reap with commands in flight.
3. **Real HAOS:** Test on a disposable/non-production HAOS instance with Protection Mode ON and the real Supervisor MQTT service; confirm startup, stop, restart, no excessive CPU/memory/thermal impact and graceful rollback to the existing `run.sh`.
4. **MQTT access control:** MQTT topic commands trust broker authentication and ACLs. Document that only authorized Home Assistant users/clients may publish to `xmrig_haos/command`; the MQTT payload alone is **not** an authorization layer.
5. **Container security and supply chain:** Pin or document base-image digest and Python dependency provenance; review outbound-only network needs, unprivileged runtime UID feasibility, Linux capabilities, and the minimum Supervisor API permission.
6. **Release procedure:** Verify branch/tag protection and required CI checks in GitHub repository settings. Main branch changes now build only; publishing requires an explicit release tag following a separate approval.

## Step 35: Mock-child restart and failure coverage

The isolated Docker runtime suite now includes four additional tests:
- Saved OFF state persists across two independently created Controllers and prevents a second mock XMRig launch.
- Corrupted state prevents launch.
- Failed ON-state persistence blocks the launch.
- OFF during scheduled crash recovery prevents later automatic restart.

The integration suite has 9 real-subprocess mock tests, 5 real-Mosquitto tests, and a separate validation suite of 226 scenarios, all verified in GitHub Actions for step 35. These tests do **not** prove real HAOS Supervisor interoperability.

**Step 36 persistence safeguard:** Before starting XMRig, the Controller atomically creates `/data/xmrig_state.json.armed` and fsyncs it. A stored ON without this marker can start; a leftover marker suppresses automatic startup (unexpected shutdown or failed OFF write). On a verified graceful shutdown with ON saved, it clears the marker so automatic ON restart still works. A successfully saved OFF clears it as well. Guard creation failures block mining. This is covered by 4 new state-store unit tests and 2 new mock-child Docker tests; restart behavior is not yet verified on actual HAOS.

**Storage limitation:** No userspace code can guarantee persistence if the underlying storage loses acknowledged writes, is irreparably damaged, or the whole volume disappears. The fail-closed guard handles ordinary write exceptions and unclean shutdowns when earlier durable guard creation succeeded; HAOS hardware testing remains required.

## Step 37: Minimum Supervisor permissions and candidate smoke test

Checked against official Home Assistant developer documentation: services with `mqtt:want` can be accessed at `GET /services/mqtt` using the injected `SUPERVISOR_TOKEN`. The service API is accessible in the default app role without enabling the broad `hassio_api: true` permission. Do not raise the Supervisor role or disable Protection Mode merely for MQTT discovery.

An additional guarded smoke script `tests/runtime/test_haos_candidate_smoke.py` executes *inside the actual candidate image* in CI with `--network none`, read-only filesystem and constrained CPU/memory. It asserts that `MiningStateStore(OFF)` and a leftover crash guard prevent process startup, with an injected failure on every attempted XMRig spawn. It does not test a real HAOS Supervisor or live MQTT credentials.

The full acceptance criteria and manual rollback plan are in `docs/HAOS_BETA_ACCEPTANCE.md`. Beta remains blocked until a disposable HAOS installation validates MQTT service access and startup behavior.

## Step 38: Separate experimental HAOS beta package

A standalone Home Assistant add-on folder `xmrig_haos_beta/` was added to the development branch with independent `config.yaml`, `Dockerfile`, and packaged Python sources. The distinct slug `xmrig_haos_beta`, `stage: experimental`, `boot: manual`, empty wallet and `mqtt:want` avoid replacing the existing stable add-on. It can be **built locally from its own folder** for an approved disposable HAOS evaluation; it is not automatically published to GHCR and is not available from the default production branch.

Beta MQTT identities are namespaced to `xmrig_haos_beta` and use a unique MQTT client ID. The CI validation checks the stable-vs-beta permission boundary and the runtime workflow independently builds `xmrig_haos_beta/` and verifies the entrypoint with a guarded OFF smoke test. This still does not replace real HAOS Supervisor or Protection Mode validation.

**Important:** GitHub repository add-on discovery uses the branch/repository actually configured in Home Assistant. The development-only beta folder does not imply availability through the normal stable repository URL. Do not change the user's production repository configuration for this test. Use a separate staging environment and follow `docs/HAOS_BETA_ACCEPTANCE.md`.

## Safe release sequence

1. Keep previous HAOS image and configuration as rollback target; back up Home Assistant.
2. Pass unit tests, real-Mosquitto integration tests, Docker mock-child runtime tests, and release-policy tests.
3. Run the Python candidate on isolated HAOS before modifying the production entrypoint.
4. Complete manual checks and resolve blockers; review PR before merge.
5. Merge to `main` only after approval, then create a verified `v2.*` release tag **only** after separate publication approval.
6. For any failure, stop the candidate and restore the existing `run.sh` version; check Supervisor health and MQTT retained Discovery entities.

This document does not authorize a merge, release, GHCR push, or installation into the user's live Home Assistant.


## README release update agreement

Keep the existing `README.md` style, language (English), title, badges, two-variant comparison, installation/configuration tables, troubleshooting, roadmap, license and donation section. Immediately before a separately approved release, update the **entire existing README** to match the features actually shipped in the production images. Explain MQTT Discovery, switch behavior, state persistence, Supervisor broker service, limitations, HAOS vs Supervised differences, and safe migration/rollback. Do not present candidate-only Python features as already installed in the published add-on. No new release or README publishing without the final release review.


## Documentation review before 2.0 release — platform support wording

- Preserve the original English README structure and visual style while updating terminology.
- Present **Home Assistant OS (HAOS Safe)** as the primary supported Home Assistant add-on platform.
- Describe **Home Assistant Supervised / MSR** as a **legacy, officially unsupported Home Assistant installation method**; do not promise continued upstream Home Assistant support.
- Clarify that **Debian 12 (Bookworm)** used as a Docker image base is not the same as claiming official support for Home Assistant Supervised on Debian 12.
- Review the Debian base image and dependency compatibility separately before deciding whether to migrate to Debian 13 (Trixie). Never upgrade the base image based solely on its version number.
- Keep the existing Supervised/MSR implementation for legacy users unless separate compatibility and migration decisions are approved.
- Review README installation table, badges, supported-platform text, comparison, MSR notes, troubleshooting and compatibility matrix together for consistent wording.
- Do not describe Python/MQTT candidate functionality as available in a published release until its production artifact is actually approved and shipped.


## Step 40: README truth review completed on develop-v2

The original English README styling, title, badges, tables, navigation, author support and PayPal link were preserved while correcting unsupported platform claims and generic performance numbers. The current stable HAOS Safe image is explicitly described as Bash `run.sh` without deployed MQTT telemetry/switch. The Python/MQTT features are described exclusively as isolated experimental beta functions, not as shipped stable capabilities. Legacy Home Assistant Supervised is identified as an unsupported installation method; Debian Bookworm is identified as a container base, not proof of Supervised support.

The `scripts/check_readme.py` validation guard checks the described stable/beta entrypoints, addon slugs, supported option names, basic source/manifest truths and author branding. The guard runs inside `.github/workflows/test.yml`. This is static consistency validation, not real HAOS user acceptance; run the full pre-release review again after any production-image changes.

Readme development edits are not a release approval. Public publication, merge to main or GHCR changes require the separately agreed release process.


## Step 41: fail-closed experimental first boot and HAOS staging runbook

The independent `xmrig_haos_beta/rootfs/app/mining_state.py` now defaults to `OFF` when its own state file is absent. This differs intentionally from the existing stable-compatible Python Controller, which still defaults to ON on a missing file. The beta requires an **explicit MQTT ON request** before it may mine. An isolated in-container smoke test `tests/runtime/test_beta_first_boot.py` fails on any attempted XMRig start during first boot. Other persisted-state and crash-guard tests remain in the candidate image suite.

`docs/HAOS_BETA_ACCEPTANCE.md` now records how to copy only the beta folder to a disposable HAOS local add-on directory, keep Protection Mode ON, check the unique `xmrig_haos_beta` MQTT namespace, capture redacted evidence and roll back by removing only the separate beta add-on. The default blank wallet intentionally fails configuration validation; even after supplying a staging-only identifier, first boot must remain OFF.

**Unverified:** successful installation and MQTT service access on real HAOS; temperature/resource policy and graceful on-device rollback. These remain beta release blockers.

README remains faithful to the stable published image; beta behavior is documented only as experimental.


## Step 44: Controller shutdown/retry lifecycle regression tests

Three isolated real mock-child subprocess tests were added to `tests/runtime/test_runtime_controller.py`:
- when crash retries are exhausted, the Controller exits nonzero, reaps its mock child and retains the persistent crash guard;
- if shutdown was requested while ON was queued, the Controller never starts mining or saves ON;
- after retry exhaustion, an explicit OFF clears the saved preference and crash guard.

A separate `tests/test_main.py` unit test verifies that the SIGTERM handler requests orderly Controller shutdown and that the prior SIGTERM/SIGINT handlers are restored after `main()` returns. This handler test uses a simulated signal callback, **not an operating-system SIGTERM delivered to a live child process**.

**Before real HAOS beta:** still require an actual SIGTERM integration test with process reaping on a disposable test system. Do not claim this is fully completed based on mocked signal handler tests alone.


## Step 45: real operating-system SIGTERM integration (isolated beta image)

`tests/runtime/test_beta_sigterm.py` creates a harmless executable Python mock child in a temporary directory. An independent Controller process runs the actual beta `app.main.main()` with operating-system signal handlers installed and a saved ON preference. The test sends **real SIGTERM to that Controller process**, waits for its clean exit, verifies the mock child PID no longer exists and that the durable crash guard has been removed while ON was preserved for a graceful restart. The CI Docker execution is network-disabled, uses a read-only root filesystem and limited CPU/memory/PIDs, and does **not** launch XMRig or contact a pool.

Scope limitation: this verifies Linux process and signal behavior in a self-contained Docker runner, not Home Assistant Supervisor delivering signals to a real add-on. Staging HAOS Supervisor shutdown/start/rollback is still a release blocker.


## Steps 46–47: hard-crash and damaged-state acceptance gates

**Step 46:** `tests/runtime/test_beta_hard_crash.py` starts the real beta Controller with a harmless mock executable, sends operating-system `SIGKILL` to its Controller process, verifies that the durable `.armed` crash guard remains despite the previously saved ON preference, and starts a fresh Controller that must stay OFF. Because SIGKILL bypasses cleanup, the test separately terminates the disposable orphan mock. **A hard-killed Controller does not itself guarantee that an existing child process immediately terminates**; Docker/HAOS cgroup and Supervisor behavior still need an actual staging-system validation.

**Step 47:** `tests/runtime/test_beta_state_recovery.py` exercises absent state, malformed JSON, incorrect types/schema version, corrupted guard contents, non-file guard and leftover valid guard; every attempt to start a miner raises a test failure. A valid persisted OFF must still allow a safe idle start. These tests run in the standalone beta Docker image without a mining pool, network, actual XMRig or Home Assistant credentials.

CI result evidence: see the matching isolated runtime workflow before marking these items passed. Both scenarios remain development-only, not substitutes for a disposable HAOS test with Protection Mode ON.


## Steps 48–52: consecutive pre-beta hardening gates (2026-10-13)

48. **Unavailable or damaged /data:** `tests/runtime/test_beta_storage_failures.py` runs with a real beta Controller and a fail-on-start XMRig stub. Missing state directory, state path substituted by a directory, rejected guard arm writes, unreadable state and unreadable guard must remain OFF. These are fault-injection tests, not physical disk failure validation.
49. **Least privileges:** `scripts/check_beta_security.py` validates the beta add-on manifest, manual boot, unique slug, optional MQTT service and absence of privileged host access. It does not prove Supervisor honors Protection Mode until an actual staging installation.
50. **Confidential log paths:** `tests/runtime/test_beta_secret_logging.py` exercises representative invalid MQTT service responses, broker startup errors and bad pool configuration, checking that fake wallet/password/token values never appear in captured logs. It does not guarantee all future library logs are secret-free.
51. **Supply chain:** `scripts/check_beta_supply_chain.py` checks XMRig 6.26.0, archive SHA256 verification and pinned `paho-mqtt==2.1.0`. Debian Bookworm base image tag, OS packages and PyPI wheel hashes are **not** yet pinned to immutable digests and remain open work.
52. **Release evidence:** `docs/BETA_RELEASE_EVIDENCE.json` and `scripts/check_beta_release_gate.py` keep beta release readiness explicitly **blocked** until separate HAOS Supervisor, Protection Mode, broker, process cleanup, rollback, resource/temperature and supply-chain evidence has been collected and a human release decision has been made.

The tests do not perform real mining and do not touch production Home Assistant, `main`, published GHCR images or release tags. Existing English README author style is unchanged. The development branch is not authorized for release by a passing CI check.
