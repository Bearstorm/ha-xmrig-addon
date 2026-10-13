#!/usr/bin/env python3
"""Create a source-only staging HAOS add-on bundle (never publish an image).

The bundle is not a release and is safe only for disposable staging HAOS.
"""
from __future__ import annotations

import hashlib
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDON = ROOT / "xmrig_haos_beta"
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)
DEST = OUT / "xmrig-haos-beta-staging-source.zip"

files = [ADDON / "config.yaml", ADDON / "Dockerfile", ADDON / "README.md"]
files += sorted((ADDON / "rootfs" / "app").glob("*.py"))
assert len(files) >= 11, "Incomplete beta source package"
assert all(f.is_file() and not f.is_symlink() for f in files)
assert not any(".env" in str(f) or "secret" in f.name.lower() for f in files)
with zipfile.ZipFile(DEST, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for item in files:
        archive_name = item.relative_to(ROOT).as_posix()
        assert archive_name.startswith("xmrig_haos_beta/")
        z.write(item, archive_name)
with zipfile.ZipFile(DEST) as z:
    assert z.testzip() is None
    assert len(z.namelist()) == len(files)
    assert len(set(z.namelist())) == len(files)
digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
(OUT / "xmrig-haos-beta-staging-source.zip.sha256").write_text(
    f"{digest}  {DEST.name}\n", encoding="ascii"
)
print(f"PASS: prepared {len(files)} beta-only source files")
print(f"SHA256: {digest}")
print("STAGING ONLY: not installed, published or validated on real Supervisor")
