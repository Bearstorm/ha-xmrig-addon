#!/usr/bin/env python3
"""Step 52: require evidence before beta release. Success means gate stayed closed."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
record=json.loads((root/"docs/BETA_RELEASE_EVIDENCE.json").read_text(encoding="utf-8"))
assert record["schema_version"] == 1
assert record["development_branch"] == "develop-v2"
assert record["candidate_slug"] == "xmrig_haos_beta"
required=(
    "haos_supervisor_real_install",
    "haos_protection_mode_on",
    "haos_real_mqtt_service",
    "haos_supervisor_process_cleanup",
    "haos_beta_rollback",
    "on_device_cpu_thermal_limits",
    "base_image_immutable_digest",
)
allowed={"not_tested","not_done","passed","failed"}
for key in required:
    assert record[key] in allowed, f"Invalid acceptance evidence: {key}"
unresolved=[key for key in required if record[key]!="passed"]
approved=record["release_approved"] is True
ready=approved and not unresolved
# This check runs on a development branch; no release is authorized here.
assert not ready, "STOP: release-ready evidence requires explicit manual review"
assert record["release_approved"] is False, "STOP: release authorization not granted"
print("PASS: release gate remains closed; real HAOS and digest evidence still required")
for key in unresolved:
    print("BLOCKED: "+key+" = "+record[key])
