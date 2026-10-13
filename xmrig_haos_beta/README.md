# XMRig Miner 2.0 — Experimental HAOS Beta Test

**This is a separate, unapproved staging add-on, not the stable HAOS Safe release.**
The existing `xmrig_haos` Dockerfile, add-on slug and `/run.sh` entrypoint remain unchanged.

- Unique slug: `xmrig_haos_beta`; boot: manual; stage: experimental
- No published GHCR image; Home Assistant must locally build this folder.
- Python Controller, HTTP telemetry, MQTT Discovery, ON/OFF command handling,
  durable mining state and unclean-shutdown guard.
- Minimal service declaration `mqtt:want` (without broad Supervisor API access).
- The default wallet is empty; add a staging-only wallet identifier to enable configuration validation. **The beta defaults Mining OFF on its first-ever start**, even if the wallet is configured. Real mining requires an explicit MQTT `ON` command.
- No production Home Assistant, broker credentials or mining pool access is needed for the CI test suite.
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


## Staging-only preparation and rollback

1. Keep the stable HAOS Safe add-on unchanged. Create a full staging HAOS backup and record the existing stable slug, settings and image.
2. On a separate disposable amd64 HAOS, copy only the `xmrig_haos_beta/` directory from the reviewed `develop-v2` commit into the **local add-on source area** (normally `/addons/local/xmrig_haos_beta`), using the supported local add-on workflow. Do not point the production add-on store to `develop-v2`.
3. Refresh the staging add-on store and check the unique beta name and slug before installing. Leave Protection Mode ON. Verify no privileged permissions are requested.
4. Configure the minimum staging values. The empty default wallet prevents initial configuration validation; do not use a production credential. Starting for the first time with valid staging configuration must leave Mining **OFF**.
5. Verify Supervisor remains healthy and MQTT entities, if the optional staging broker is present, appear only under `xmrig_haos_beta`. Do not publish `ON` until a separately approved resource-bounded test.
6. To roll back, turn Mining OFF, stop the beta add-on, uninstall the beta test package, remove its retained MQTT Discovery records if needed, and restore the staging backup if checks fail. The existing stable `xmrig_haos` add-on and data must not be modified.

**Not yet verified:** installing on a real HAOS Supervisor or demonstrating Protection Mode compatibility. GitHub CI builds the package and forbids actual mining; it cannot replace the staging acceptance test.
