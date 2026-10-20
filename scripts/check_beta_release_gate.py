#!/usr/bin/env python3
"""Check beta.2 technical evidence without treating optional stress tests as blockers.

A public release still requires explicit maintainer approval; a green CI job
alone is not release authorization.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
record = json.loads((root / "docs/BETA_RELEASE_EVIDENCE.json").read_text(encoding="utf-8"))

assert record["schema_version"] == 1
assert record["development_branch"] == "develop-v2"
assert record["candidate_slug"] == "xmrig_haos_beta"

required = (
    "ci_docker_mock_tests",
    "haos_supervisor_real_install",
    "haos_protection_mode_on",
    "haos_real_mqtt_service",
    "base_image_immutable_digest",
)
optional = (
    "haos_supervisor_process_cleanup",
    "haos_beta_rollback",
    "on_device_cpu_thermal_limits",
)
allowed = {"not_tested", "not_done", "passed", "failed"}
for key in (*required, *optional):
    assert record[key] in allowed, f"Invalid acceptance evidence: {key}"

assert isinstance(record["release_approved"], bool), "Approval must be boolean"
missing = [key for key in required if record[key] != "passed"]
if missing:
    for key in missing:
        print(f"BLOCKED: required {key} = {record[key]}")
    raise SystemExit("Beta technical release gate failed.")

print("PASS: mandatory beta.2 technical evidence is recorded.")
for key in optional:
    if record[key] != "passed":
        print(f"DISCLOSED, NON-BLOCKING: {key} = {record[key]}")

if record["release_approved"]:
    print("APPROVED: maintainer has explicitly authorized beta pre-release.")
else:
    print("PENDING: public beta pre-release requires explicit maintainer approval.")
