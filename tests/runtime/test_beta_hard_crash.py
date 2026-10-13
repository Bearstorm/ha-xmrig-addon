"""Simulate a hard Controller crash, then verify safe restart.

Uses only a disposable mock executable in network-disabled CI.
"""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.mining_state import MiningStateStore
from app.config import MinerConfig
from app.main import Controller
from app.miner_manager import MinerManager

MOCK = """#!/usr/bin/env python3
import os,time
from pathlib import Path
Path(os.environ["BETA_TEST_PID_PATH"]).write_text(str(os.getpid()))
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
config=MinerConfig(pool="example.invalid",port=443,wallet="FAKE-CI",worker="TEST",threads=1,priority=2,tls_mode="auto")
raise SystemExit(main(config_loader=lambda:config,
 manager_factory=lambda c:MinerManager(c,binary=sys.argv[1]),
 monitor_factory=lambda:None,publisher_factory=lambda:None,
 state_store_factory=lambda:MiningStateStore(Path(sys.argv[2])),install_signals=True))
"""


def wait_for(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.03)
    return predicate()


def run():
    with tempfile.TemporaryDirectory(prefix="beta-hard-crash-") as directory:
        root = Path(directory)
        binary = root / "mock"
        binary.write_text(MOCK)
        binary.chmod(0o700)
        store = MiningStateStore(root / "state.json")
        store.save(True)
        pid_path = root / "mock.pid"
        env = os.environ.copy()
        env["BETA_TEST_PID_PATH"] = str(pid_path)
        controller = subprocess.Popen(
            [sys.executable, "-c", RUNNER, str(binary), str(store.path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
        )
        child_pid = None
        try:
            assert wait_for(lambda: store.guard_exists() and pid_path.exists()), "Controller never started mock"
            child_pid = int(pid_path.read_text())
            controller.kill()
            controller.wait(timeout=4)
            assert controller.returncode != 0
            assert store.guard_exists(), "SIGKILL must leave guard armed"
            assert store.load() is True, "Saved ON remains, but guard takes precedence"

            second_manager = MinerManager(
                MinerConfig(pool="example.invalid",port=443,wallet="FAKE-CI",
                            worker="TEST",threads=1,priority=2,tls_mode="auto"),
                binary=str(binary),
            )
            # If the guard is ignored, the attempted launch is a hard test failure.
            def reject_spawn():
                raise AssertionError("Unexpected mock launch after SIGKILL")
            second_manager.start = reject_spawn
            import threading
            stopped = threading.Event()
            second = Controller(second_manager, state_store=store,
                                stop_event=stopped, poll_interval=0.02)
            done = threading.Timer(0.2, second.request_shutdown)
            done.start()
            try:
                assert second.run() == 0
            finally:
                done.join(timeout=2)
            assert store.guard_exists(), "Restart must not clear crash guard"
            assert second_manager.pid is None
            print("PASS: SIGKILL retains crash guard; next Controller stays safely OFF")
        finally:
            if controller.poll() is None:
                controller.kill()
                controller.wait(timeout=4)
            if child_pid is not None:
                # SIGKILL bypasses Controller teardown; clean up orphaned mock.
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    run()
