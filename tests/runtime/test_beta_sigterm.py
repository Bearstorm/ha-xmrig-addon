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
import os
import signal
import sys
import time
from pathlib import Path
def stop(*args):
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
Path(os.environ["BETA_MOCK_PID_FILE"]).write_text(str(os.getpid()))
print("MOCK_STARTED", flush=True)
while True:
    time.sleep(0.05)
"""

RUNNER = """
import sys
from pathlib import Path
from app.config import MinerConfig
from app.main import Controller
from app.miner_manager import MinerManager
from app.mining_state import MiningStateStore
import signal
config = MinerConfig(pool="example.invalid", port=443, wallet="CI-PLACEHOLDER",
                     worker="TEST", threads=1, priority=2, tls_mode="auto")
manager = MinerManager(config, binary=sys.argv[1])
controller = Controller(manager, state_store=MiningStateStore(Path(sys.argv[2])),
                        auto_start=True, poll_interval=0.05)
signal.signal(signal.SIGTERM, lambda _sig, _frame: controller.request_shutdown())
signal.signal(signal.SIGINT, lambda _sig, _frame: controller.request_shutdown())
raise SystemExit(controller.run())
"""


def run():
    with tempfile.TemporaryDirectory(prefix="beta-sigterm-") as dirname:
        root = Path(dirname)
        mock = root / "mock-child"
        mock.write_text(MOCK, encoding="utf-8")
        mock.chmod(0o700)
        store = MiningStateStore(root / "mining.json")
        store.save(True)
        pid_file = root / "mock.pid"
        child_env = os.environ.copy()
        child_env["BETA_MOCK_PID_FILE"] = str(pid_file)
        controller = subprocess.Popen(
            [sys.executable, "-c", RUNNER, str(mock), str(store.path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_env,
        )
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not store.guard_exists():
                if controller.poll() is not None:
                    raise AssertionError("Controller exited before signal test")
                time.sleep(0.05)
            assert store.guard_exists(), "Miner must arm crash guard before launch"
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not pid_file.exists():
                if controller.poll() is not None:
                    raise AssertionError("Controller exited before mock child started")
                time.sleep(0.05)
            assert pid_file.exists(), "Mock child never started"
            child_pid = int(pid_file.read_text())
            controller.send_signal(signal.SIGTERM)
            out, err = controller.communicate(timeout=8)
            assert controller.returncode == 0, f"Controller failed: {err[-500:]!r}"
            assert store.load() is True, "ON preference should survive clean shutdown"
            assert not store.guard_exists(), "Graceful shutdown must clear guard"
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise AssertionError("Mock child still alive after Controller SIGTERM")
            print("PASS: real SIGTERM reaps mock child and clears crash guard")
        finally:
            if controller.poll() is None:
                controller.kill()
                controller.wait(timeout=3)


if __name__ == "__main__":
    run()
