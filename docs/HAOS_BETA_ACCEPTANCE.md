# XMRig 2.0 — HAOS Safe isolated beta acceptance checklist

**Development only:** this is a staging checklist, not permission to modify a live Home Assistant, merge to `main`, publish to GHCR or create a release.

## Security and Supervisor MQTT contract

- The candidate declares `services: [mqtt:want]` so the absence of Mosquitto does not stop mining. The official Supervisor services API supports authenticated `GET /services/mqtt` using the injected `SUPERVISOR_TOKEN`.
- A service client can use `/services*` with default API privileges. Do **not** add `hassio_api: true`, `homeassistant_api: true`, `hassio_role: admin`, `full_access: true`, host network, host PID, privileged capabilities or extra volumes just for this endpoint.
- `MQTT_COMMAND_TOPIC=xmrig_haos_beta/command` is **not** an environment feature; this notation documents the topic only. Broker authentication and ACLs are the security boundary. Grant publish access only to trusted controllers and the Home Assistant MQTT integration.
- Do not log `SUPERVISOR_TOKEN`, MQTT password or wallet. Do not expose Supervisor HTTP service outside the add-on network.
- If Supervisor service is absent, the candidate's optional MQTT adapter is disabled; this must not affect process supervision.
- Live Supervisor API credential provision, broker ACLs, and Protection Mode operation are **not** proven by GitHub Actions.

## Before any beta deployment

1. Create a Home Assistant backup, preserve the current add-on image/version and settings, and confirm restore procedure. Never test an unapproved candidate on the production HAOS.
2. Prepare an independent disposable HAOS instance on amd64 with the intended Supervisor version and Protection Mode ON.
3. Confirm the staging Mosquitto provider has registered the MQTT service and that only authorized identities can publish to `xmrig_haos_beta/command`.
4. Build/test the candidate in GitHub Actions: syntax/units, mock-child controller, real local Mosquitto, and candidate OFF smoke test.
5. Install a separately packaged test candidate on staging HAOS only after explicit approval. Confirm Supervisor status stays healthy; CPU and temperature remain within limits.
6. With no real mining credentials first, verify starting with saved OFF and with a leftover crash guard never spawns XMRig. Check telemetry state and MQTT unavailability.
7. With disposable test credentials and an explicitly approved mining test window, confirm ON, OFF, graceful restart ON, persistent OFF, broker drop/reconnect, invalid/retained commands, SIGTERM and bounded crash recovery.
8. Stop the candidate and restore the existing stable `run.sh` add-on; verify Supervisor health and MQTT retained Discovery cleanup or migration.

## Step 41 — isolated installation and rollback procedure

**Scope:** disposable Home Assistant OS (amd64), local add-on only, separate broker and data. Do not add the beta source to a production HAOS instance.

1. **Backup:** Create a full backup of the disposable HAOS, confirm its restore method, and record Supervisor/core/add-on versions. Preserve the stable `xmrig_haos` manifest, slug, settings, Docker image and `/run.sh` entrypoint unchanged.
2. **Install source:** Select a reviewed `develop-v2` commit, copy *only* its `xmrig_haos_beta` directory into the staging local add-on directory (typically `/addons/local/xmrig_haos_beta`). Reload the add-on store. Do **not** change the normal GitHub repository URL or install the branch on production.
3. **Review before start:** Confirm slug `xmrig_haos_beta`, `boot: manual`, `stage: experimental`, `services: [mqtt:want]`, Protection Mode **ON**, host PID/network and full access **OFF**. Check no unexpected shared volume/host device permissions.
4. **First run without mining:** Supply a *staging-only* nonsecret wallet identifier so the beta configuration validator accepts the options (the default wallet is intentionally blank). Start the beta. The first-ever beta state file is missing, so `MiningStateStore.load()` must default to **OFF**. Observe logs, process status and Supervisor health. This first-boot OFF behavior is covered by an independent Docker test, **not yet confirmed on HAOS**.
5. **Supervisor MQTT:** With optional staging Mosquitto, verify only `xmrig_haos_beta/#` and `homeassistant/*/xmrig_haos_beta/*/config` Discovery topics are used; no stable `xmrig_haos/command` topic is consumed. Check broker ACLs; **never expose Supervisor or broker credentials in screenshots/logs**.
6. **Explicit ON test gate:** Do not send `ON` until an approved short test window with appropriate CPU, memory and temperature constraints. Then check ON/OFF, saved OFF after restart, graceful ON restart, unclean-shutdown guard, disconnected broker and retained command rejection. **Do not run this on production HAOS.**
7. **Rollback:** Send OFF when the beta is running, stop the beta, uninstall its **separate** slug and remove only its beta MQTT retained Discovery records where appropriate; check Supervisor health. Restore the staging backup if required. Stable `xmrig_haos` and its config must remain unchanged throughout.

**Stop conditions:** Supervisor unhealthy; Protection Mode needs disabling; privileged host access requested; unexpectedly launched XMRig during OFF; wrong MQTT namespace; missing safe rollback; excessive CPU temperature or unbounded restarts. Record a failing test and stop; do not silently loosen security settings.

**Evidence:** Save the staging version matrix, time of test, masked Supervisor MQTT response status (no token/secret), observed switch ON/OFF states, process PID changes, relevant redacted logs and screenshots, and proof of rollback. Mark unperformed checks as **not tested**, not passed.

## Exit criteria

**No beta release until**: the actual HAOS permissions and MQTT service pass the staging run; release-policy and Docker smoke checks pass; migration/rollback is demonstrated; memory/temperature policy and permissions are reviewed; README and changelog accurately describe only shipped features.

## Reconciliation with current development status

The published HAOS add-on still runs `/bin/bash /run.sh`. The Python + MQTT functionality exists only in the test candidate Dockerfile. Passing a `--network none` Docker test does not establish compatibility with the real Supervisor.


## Step 39: simulated Supervisor API acceptance gate

GitHub Actions now tests the beta module against a **local mock Supervisor HTTP service**, exercising the expected `GET /services/mqtt` contract, `Bearer` authorization, missing/rejected tokens, broker credentials and optional MQTT fallback. It also checks that beta command topics and retained Discovery entity topics do not overlap with the stable HAOS namespace. The simulated service uses a fake token and never connects to a real HAOS or mining pool.

**Evidence boundary:** A mock Supervisor validates client behavior, not Supervisor compatibility or HAOS runtime permissions. A separate staging HAOS install with Protection Mode ON and a real Supervisor-provided MQTT service remains mandatory before release. Production HAOS access is out of scope.


## Step 42 — full beta entrypoint/options.json preflight

The CI beta package job now runs `tests/runtime/test_beta_entrypoint_options.py` inside the **independently built beta Docker image**, with `--network none`, CPU/memory/PID limits, no host privileges, a read-only root filesystem and an ephemeral writable `/data` tmpfs.

The script exercises the real `app.main.main()` wiring, the actual `app.config.load_config()` default `/data/options.json` path, and the production `MiningStateStore` default `/data/xmrig_state.json` path. It substitutes a fail-on-spawn method so any attempt to start XMRig would fail CI. Checks include:
- a valid staging `options.json` with absent state must boot and remain Mining OFF;
- a persisted ON together with a crash guard must refuse to auto-start;
- malformed `options.json` must return a controlled startup error;
- an empty wallet must return a controlled configuration error.

The test uses no real credentials, real mining, real Supervisor token or HAOS installation. **It does not establish actual HAOS Supervisor, Protection Mode, MQTT ACL or resource/thermal compatibility.** On-device staging acceptance and rollback evidence remain mandatory before a beta release.
