"""Real operating-system SIGTERM smoke for the beta Controller.

Runs only in isolated CI. Uses a harmless test child instead of XMRig.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.mining_state import MiningStateStore

MOCK = """#!/usr/bin/env python3
import signal
import sys
import time
def stop(*args):
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
print("MOCK_STARTED", flush=True)
while True:
    time.sleep(0.05)
"""

RUNNER = """
import sys
from pathlib import Path
from app.config import MinerConfig
from app.main import main
from app.miner_manager import MinerManager
from app.mining_state import MiningStateStore
config = MinerConfig(pool="example.invalid", port=443, wallet="CI-PLACEHOLDER",
                     worker="TEST", threads=1, priority=2, tls_mode="auto")
raise SystemExit(main(
    config_loader=lambda: config,
    manager_factory=lambda c: MinerManager(c, binary=sys.argv[1]),
    monitor_factory=lambda: None,
    publisher_factory=lambda: None,
    state_store_factory=lambda: MiningStateStore(Path(sys.argv[2])),
    install_signals=True,
))
"""


def run():
    with tempfile.TemporaryDirectory(prefix="beta-sigterm-") as dirname:
        root = Path(dirname)
        mock = root / "mock-child"
        mock.write_text(MOCK, encoding="utf-8")
        mock.chmod(0o700)
        store = MiningStateStore(root / "mining.json")
        store.save(True)
        controller = subprocess.Popen(
            [sys.executable, "-c", RUNNER, str(mock), str(store.path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not store.guard_exists():
                if controller.poll() is not None:
                    raise AssertionError("Controller exited before signal test")
                time.sleep(0.05)
            assert store.guard_exists(), "Miner must arm crash guard before launch"
            time.sleep(0.3)
            controller.send_signal(signal.SIGTERM)
            out, err = controller.communicate(timeout=8)
            assert controller.returncode == 0, f"Controller failed: {err[-500:]!r}"
            assert store.load() is True, "ON preference should survive clean shutdown"
            assert not store.guard_exists(), "Graceful shutdown must clear guard"
            print("PASS: real SIGTERM exits cleanly and clears crash guard")
        finally:
            if controller.poll() is None:
                controller.kill()
                controller.wait(timeout=3)


if __name__ == "__main__":
    run()
