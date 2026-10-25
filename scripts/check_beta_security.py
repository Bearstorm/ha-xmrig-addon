#!/usr/bin/env python3
"""Step 49: fail release checks if beta asks for new host-level privileges."""
from pathlib import Path
import yaml

root=Path(__file__).resolve().parents[1]
addon=root/"xmrig_haos_beta"
cfg=yaml.safe_load((addon/"config.yaml").read_text(encoding="utf-8"))
docker=(addon/"Dockerfile").read_text(encoding="utf-8")
must_false=("host_network","host_pid","full_access","hassio_api",
            "docker_api","kernel_modules","uart","usb","udev","video","audio")
for key in must_false:
    assert cfg.get(key,False) is False, f"Unsafe beta setting: {key}"
assert cfg.get("homeassistant_api") is True  # Optional Core API for thermal monitoring only
assert cfg.get("apparmor") is True
assert cfg.get("init") is False
assert cfg.get("boot") == "manual"
assert cfg.get("stage") == "experimental"
assert cfg.get("slug") == "xmrig_haos_beta"
assert cfg.get("services") == ["mqtt:want"]
assert cfg["options"]["wallet"] == ""
for key in ("devices","privileged","map","host_ipc","host_uts","host_dbus",
            "host_docker","host_mounts","host_paths"):
    assert not cfg.get(key), f"Unexpected host permission: {key}"
assert "COPY rootfs/app/ /opt/xmrig/app/" in docker
assert 'ENTRYPOINT ["/opt/xmrig-venv/bin/python", "-m", "app.main"]' in docker
assert "sha256sum -c -" in docker
for bad in ("--privileged","--cap-add","/var/run/docker.sock","/dev/cpu",
            "ADD https://","curl | bash"):
    assert bad not in docker, f"Unsafe Dockerfile term: {bad}"
print("PASS: experimental beta uses isolated slug, manual boot and minimum HAOS permissions")
print("NOTE: static checks do not prove actual HAOS Protection Mode compatibility")
