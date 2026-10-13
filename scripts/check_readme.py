#!/usr/bin/env python3
"""Keep README claims aligned with actual shipped add-on manifests and entrypoints.

Static release documentation guard; no network, mining or Home Assistant access.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
readme = (ROOT / "README.md").read_text(encoding="utf-8")
stable = yaml.safe_load((ROOT / "xmrig_haos/config.yaml").read_text(encoding="utf-8"))
legacy = yaml.safe_load((ROOT / "xmrig/config.yaml").read_text(encoding="utf-8"))
beta = yaml.safe_load((ROOT / "xmrig_haos_beta/config.yaml").read_text(encoding="utf-8"))
stable_docker = (ROOT / "xmrig_haos/Dockerfile").read_text(encoding="utf-8")
beta_docker = (ROOT / "xmrig_haos_beta/Dockerfile").read_text(encoding="utf-8")

def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("README CONTRACT FAILED: " + message)

ensure(stable["slug"] == "xmrig_haos", "stable slug changed")
ensure(beta["slug"] != stable["slug"], "beta must use separate slug")
ensure(stable["full_access"] is False and beta["full_access"] is False,
       "HAOS and beta permission claims invalid")
ensure(legacy["full_access"] is True, "legacy privileges changed")
ensure("ENTRYPOINT [\"/bin/bash\", \"/run.sh\"]" in stable_docker,
       "stable startup changed; review README and tests")
ensure('ENTRYPOINT ["/opt/xmrig-venv/bin/python", "-m", "app.main"]' in beta_docker,
       "beta startup changed; review README and tests")
ensure("MQTT Discovery, MQTT Mining switch or persisted Mining ON/OFF" in readme,
       "stable feature availability disclaimer missing")
ensure("no longer an officially supported Home Assistant installation method" in readme,
       "legacy Supervised support warning missing")
ensure("not yet validated on a real HAOS Supervisor" in readme,
       "beta validation status missing")
ensure("Debian Bookworm (12)" in readme,
       "container base wording missing")
ensure("Support me 🔥" in readme and "PVATF8G5NZ392" in readme,
       "author donation identity must be preserved")
for option in stable["schema"]:
    ensure(f"`{option}`" in readme, f"stable option {option} undocumented")
ensure("`msr_mod`" in readme and "`tls_mode`" in readme,
       "distinct variant settings missing")
ensure("## ⚙ Configuration" in readme and "## 📥 Installation" in readme,
       "original heading structure lost")
ensure("HAOS 10 |" not in readme and "HAOS 11 |" not in readme,
       "obsolete kernel compatibility table restored")
ensure("~20%" not in readme and "15–25°C" not in readme,
       "unverified universal performance claims restored")
print("PASS: README accurately separates stable, legacy and experimental beta")
print("PASS: original author branding, installation, configuration and support sections kept")
