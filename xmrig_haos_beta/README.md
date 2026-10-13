# XMRig Miner 2.0 — Experimental HAOS Beta Test

**This is a separate, unapproved staging add-on, not the stable HAOS Safe release.**
The existing `xmrig_haos` Dockerfile, add-on slug and `/run.sh` entrypoint remain unchanged.

- Unique slug: `xmrig_haos_beta`; boot: manual; stage: experimental
- No published GHCR image; Home Assistant must locally build this folder.
- Python Controller, HTTP telemetry, MQTT Discovery, ON/OFF command handling,
  durable mining state and unclean-shutdown guard.
- Minimal service declaration `mqtt:want` (without broad Supervisor API access).
- The default wallet is empty. Configure only on disposable, separately approved staging HAOS.
- Beta MQTT command and Discovery topics use the separate `xmrig_haos_beta` namespace;
  client ID is also unique. Still test exclusively on a disposable HAOS instance.
- This add-on has not yet been verified on a live HAOS Supervisor.
- No upgrade path or release authorization is implied by adding the folder.

**Test sequence:** read `docs/HAOS_BETA_ACCEPTANCE.md` before installing.
Back up the staging environment and verify rollback to the stable image.
For actual XMRig running, acquire explicit authorization and define limits.

Source modules in `rootfs/app` are intentionally copied from the
`xmrig_haos/rootfs/app` candidate. CI verifies byte-identical shared modules while intentionally allowing isolated
MQTT identities in the beta copy. Update shared code in both locations.
