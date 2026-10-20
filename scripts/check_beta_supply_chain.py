#!/usr/bin/env python3
"""Step 51: document and enforce the current beta artifact supply-chain invariants.

Do not imply immutable base-image pinning: Bookworm is a moving tag.
"""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
beta=(root/"xmrig_haos_beta/Dockerfile").read_text(encoding="utf-8")
stable=(root/"xmrig_haos/Dockerfile").read_text(encoding="utf-8")

version=re.search(r"^ARG XMRIG_VERSION=([0-9]+\.[0-9]+\.[0-9]+)$",beta,re.M)
checksum=re.search(r"^ARG XMRIG_SHA256=([0-9a-f]{64})$",beta,re.M)
assert version and version.group(1) == "6.26.0"
assert checksum and checksum.group(1) != "0"*64
assert "sha256sum -c -" in beta
assert '"paho-mqtt==2.1.0"' in beta
assert "apt-get install -y --no-install-recommends" in beta
assert "COPY rootfs/app/ /opt/xmrig/app/" in beta
assert "ENTRYPOINT" in beta
assert "push:" not in beta and "ghcr.io/home-assistant/amd64-base-debian:bookworm" in beta
assert "@sha256:" not in beta.splitlines()[2], "Re-evaluate this audit after immutable base pin"
assert "ENTRYPOINT" in stable
print("PASS: verified XMRig version and archive SHA256 check, pinned paho-mqtt version")
print("OPEN: base image is tagged Bookworm, not pinned by digest")
print("OPEN: apt packages and paho distribution hashes are not immutable")
