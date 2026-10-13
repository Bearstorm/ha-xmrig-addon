# XMRig 2.0 — HAOS Safe isolated beta acceptance checklist

**Development only:** this is a staging checklist, not permission to modify a live Home Assistant, merge to `main`, publish to GHCR or create a release.

## Security and Supervisor MQTT contract

- The candidate declares `services: [mqtt:want]` so the absence of Mosquitto does not stop mining. The official Supervisor services API supports authenticated `GET /services/mqtt` using the injected `SUPERVISOR_TOKEN`.
- A service client can use `/services*` with default API privileges. Do **not** add `hassio_api: true`, `homeassistant_api: true`, `hassio_role: admin`, `full_access: true`, host network, host PID, privileged capabilities or extra volumes just for this endpoint.
- `MQTT_COMMAND_TOPIC=xmrig_haos/command` is **not** an environment feature; this notation documents the topic only. Broker authentication and ACLs are the security boundary. Grant publish access only to trusted controllers and the Home Assistant MQTT integration.
- Do not log `SUPERVISOR_TOKEN`, MQTT password or wallet. Do not expose Supervisor HTTP service outside the add-on network.
- If Supervisor service is absent, the candidate's optional MQTT adapter is disabled; this must not affect process supervision.
- Live Supervisor API credential provision, broker ACLs, and Protection Mode operation are **not** proven by GitHub Actions.

## Before any beta deployment

1. Create a Home Assistant backup, preserve the current add-on image/version and settings, and confirm restore procedure. Never test an unapproved candidate on the production HAOS.
2. Prepare an independent disposable HAOS instance on amd64 with the intended Supervisor version and Protection Mode ON.
3. Confirm the staging Mosquitto provider has registered the MQTT service and that only authorized identities can publish to `xmrig_haos/command`.
4. Build/test the candidate in GitHub Actions: syntax/units, mock-child controller, real local Mosquitto, and candidate OFF smoke test.
5. Install a separately packaged test candidate on staging HAOS only after explicit approval. Confirm Supervisor status stays healthy; CPU and temperature remain within limits.
6. With no real mining credentials first, verify starting with saved OFF and with a leftover crash guard never spawns XMRig. Check telemetry state and MQTT unavailability.
7. With disposable test credentials and an explicitly approved mining test window, confirm ON, OFF, graceful restart ON, persistent OFF, broker drop/reconnect, invalid/retained commands, SIGTERM and bounded crash recovery.
8. Stop the candidate and restore the existing stable `run.sh` add-on; verify Supervisor health and MQTT retained Discovery cleanup or migration.

## Exit criteria

**No beta release until**: the actual HAOS permissions and MQTT service pass the staging run; release-policy and Docker smoke checks pass; migration/rollback is demonstrated; memory/temperature policy and permissions are reviewed; README and changelog accurately describe only shipped features.

## Reconciliation with current development status

The published HAOS add-on still runs `/bin/bash /run.sh`. The Python + MQTT functionality exists only in the test candidate Dockerfile. Passing a `--network none` Docker test does not establish compatibility with the real Supervisor.
