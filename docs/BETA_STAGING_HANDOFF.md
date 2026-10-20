# XMRig Miner 2.0 — Beta staging handoff

> **Status: PRE-RELEASE CANDIDATE, NOT PUBLISHED.**
> Real HAOS beta.2 checks have been recorded for one operator host; see
> `docs/BETA_RELEASE_EVIDENCE.json` and `docs/RELEASE_NOTES_v2.0.0-beta.2.md`.
> Do not create a public pre-release without explicit maintainer approval.
> This source-only beta is not a supported stable add-on or a GHCR image release.

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

## Recorded beta.2 acceptance evidence (2026-10-19)

The table below summarizes recorded results, not new tests performed by this
handoff document. The machine-readable record in
`docs/BETA_RELEASE_EVIDENCE.json` is authoritative for release-gate values;
`docs/RELEASE_NOTES_v2.0.0-beta.2.md` explains the observed measurements and
scope. Results apply to the operator's one HAOS installation, not all hardware.

| Gate | Recorded state | Scope / limitation |
|---|---|---|
| CI and isolated Docker/mock tests | PASSED | CI records; not a substitute for real HAOS |
| HAOS Supervisor real install and beta.0 → beta.1 → beta.2 updates | PASSED | Local standalone beta add-on on one HAOS host |
| Protection Mode ON | PASSED | No privilege escalation introduced |
| Real Supervisor-provided MQTT service | PASSED | Discovery, Mining ON/OFF and resource telemetry observed |
| Supervisor unexpected process cleanup | NOT TESTED | Isolated failure-injection coverage only; deliberate production crash deferred |
| Beta-only rollback installation | NOT TESTED | Backups/source archives retained; actual rollback deferred |
| Sustained on-device CPU/thermal limits | NOT TESTED | Short observation only: 76 °C at 58% load, then 63 °C at 27% after Mining OFF; not sustained acceptance |
| Immutable base image digest | PASSED | Reviewed pinned digest and isolated CI build; does not establish identity of an earlier operator-installed image |

Additional recorded beta.2 measurements: four mining threads on a host with
12 logical CPUs produced approximately 33.33% normalized CPU use; after
Mining OFF the add-on RAM was approximately 14.69 MiB. These observations are
not guarantees for other hosts or configurations.

**Release decision:** `release_approved: false` at the time of this record.
An experimental source-only pre-release requires separate explicit maintainer
approval. Do not merge into `main`, push GHCR images or change the stable
`xmrig_haos` add-on as part of this documentation alignment.

**Never mark a gate passed from a mock API or a Docker-only test.** The deferred
production crash, rollback and sustained thermal tests are disclosed,
non-blocking limitations for this experimental beta under the recorded policy;
do not silently relabel them as passed.

## README and release discipline

Keep the author's original English README layout, badges, tables and donation
section. The repository's normal README must not claim beta features as
features of the currently published HAOS Safe image. Any future beta
announcement must explicitly list what passed on the real HAOS, what remains
experimental and how to roll back.
