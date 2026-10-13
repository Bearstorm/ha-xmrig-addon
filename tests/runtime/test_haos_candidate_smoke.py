"""HAOS Python candidate smoke test, using its installed Controller and manager.

No actual miner is ever started. This script injects a guard that makes ANY
attempt to spawn XMRig a test failure. The candidate runs without a broker,
Home Assistant, or network access.
"""
from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

from app.config import MinerConfig
from app.main import Controller
from app.miner_manager import MinerManager
from app.mining_state import MiningStateStore

CONFIG = MinerConfig(
    pool="example.invalid",
    port=443,
    wallet="DUMMY-NOT-A-WALLET",
    worker="CI",
    threads=2,
    priority=2,
    tls_mode="auto",
)


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="xmrig-candidate-safe-") as directory:
        store = MiningStateStore(Path(directory) / "xmrig_state.json")
        store.save(False)
        manager = MinerManager(CONFIG)
        stop = threading.Event()
        controller = Controller(
            manager,
            state_store=store,
            stop_event=stop,
            poll_interval=0.02,
        )

        def request_stop():
            time.sleep(0.2)
            controller.request_shutdown()

        thread = threading.Thread(target=request_stop, daemon=True)
        thread.start()
        with patch.object(manager, "start", side_effect=AssertionError("XMRig started despite OFF")):
            result = controller.run()
        thread.join(timeout=2)
        assert result == 0, f"Controller returned {result}"
        assert manager.pid is None
        assert not store.load()
        assert not store.guard_exists()
        print("PASS: Candidate Controller boots OFF and exits without running XMRig")

        store.save(True)
        store.arm()
        controller2 = Controller(
            MinerManager(CONFIG),
            state_store=store,
            stop_event=threading.Event(),
            poll_interval=0.02,
        )
        def request_stop2():
            time.sleep(0.2)
            controller2.request_shutdown()
        thread2 = threading.Thread(target=request_stop2, daemon=True)
        thread2.start()
        with patch.object(controller2._manager, "start", side_effect=AssertionError("Armed state started miner")):
            result2 = controller2.run()
        thread2.join(timeout=2)
        assert result2 == 0
        assert store.guard_exists()
        print("PASS: Candidate Controller blocks auto-start after unclean shutdown")


if __name__ == "__main__":
    run()
