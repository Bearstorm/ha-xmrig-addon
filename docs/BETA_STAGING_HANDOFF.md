# XMRig Miner 2.0 — Beta staging handoff

> **Status: PRE-RELEASE CANDIDATE, NOT PUBLISHED.**
> Complete the real HAOS checks before creating a beta tag, uploading GHCR images,
> or presenting this as a supported Home Assistant add-on.

## CI evidence

The `develop-v2` **XMRig HAOS - Isolated Runtime Test** workflow must be green.
Its job **Package beta source for disposable HAOS staging (not a release)**
attaches a short-lived `xmrig-haos-beta-staging-source` artifact. It contains a
source ZIP and a SHA-256 file. The ZIP includes **only** the independent beta
directory `xmrig_haos_beta/`, not the stable add-on or secrets.

The artifact is a **source bundle for a local HAOS build**, not a Docker image
and not a public release. Verify the SHA-256 before extracting.

## Staging-only operator procedure

1. Prepare a separate disposable HAOS amd64 test instance, not the home system.
   Record HAOS/Core/Supervisor versions, create a full backup, and confirm the
   restore operation is available.
2. Download the artifact from the successful workflow run for the exact reviewed
   commit. Verify its checksum. Extract **only** `xmrig_haos_beta/` into the
   local add-on source area of staging HAOS (typically
   `/addons/local/xmrig_haos_beta/`).
3. Reload the add-on store and inspect the local experimental add-on.
   Ensure slug `xmrig_haos_beta`, manual boot, full_access false,
   host_network false, host_pid false, Protection Mode ON. Abort if the actual
   Supervisor installation requests additional privileges or cannot install.
4. Supply a disposable dummy wallet identifier in the staging options. Leave
   the beta in its first-boot **Mining OFF** state. Start the add-on with
   **no MQTT ON command**. Confirm Supervisor and Core health, clean logs,
   no XMRig process, and expected OFF telemetry.
5. On the *isolated staging broker*, check Supervisor-supplied MQTT service
   credentials (do not expose them), broker subscriptions and Home Assistant
   Discovery under `xmrig_haos_beta`. No control or Discovery topics may
   overlap with the stable `xmrig_haos` namespace. Test MQTT absence/failure
   without mining.
6. If explicitly approved for a short, resource-limited mining test, replace
   fake credentials with staging-only credentials; set thermal/memory/CPU limits;
   validate fresh ON, OFF, clean restart and broker reconnect. Do not mine on the
   production home system. Disconnecting MQTT is **not** an emergency stop.
7. For rollback, explicitly send OFF if reachable, stop/uninstall only the
   beta slug, clear retained beta Discovery records as needed, and verify
   Supervisor health. Restore staging backup if anything fails. The stable
   `xmrig_haos` add-on and MQTT identities must never be modified.

## Record acceptance

| Gate | Evidence to record | Initial state |
|---|---|---|
| HAOS Supervisor real install | version + redacted screenshot | NOT TESTED |
| Protection Mode ON | add-on security screenshot | NOT TESTED |
| Supervisor-provided MQTT | broker test + redacted log | NOT TESTED |
| Supervisor shutdown/reap | PID and exit result | NOT TESTED |
| Beta-only rollback | backup/restore and MQTT cleanup | NOT TESTED |
| CPU/thermal/memory | time-limited test measurements | NOT TESTED |
| Immutable image dependencies | approved digest/hash review | NOT DONE |

See `docs/BETA_RELEASE_EVIDENCE.json` for the machine-readable gate state.
**Never mark a gate passed from a mock API or a Docker-only test.** After
actual results are documented, independently review them before public beta
release.

## README and release discipline

Keep the author's original English README layout, badges, tables and donation
section. The repository's normal README must not claim beta features as
features of the currently published HAOS Safe image. Any future beta
announcement must explicitly list what passed on the real HAOS, what remains
experimental and how to roll back.
