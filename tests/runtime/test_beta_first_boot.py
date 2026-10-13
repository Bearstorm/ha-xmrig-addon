"""First-run beta safety checks inside the independent beta Docker image.

Requires no MQTT, Supervisor, network or wallet. Any XMRig spawn fails the test.
"""
from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from app.config import MinerConfig
from app.main import Controller
from app.miner_manager import MinerManager
from app.mining_state import MiningStateStore


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="xmrig-beta-first-boot-") as root:
        state = MiningStateStore(Path(root) / "xmrig_state.json")
        assert state.load() is False, "Beta must start OFF if no saved preference"
        config = MinerConfig(
            pool="example.invalid", port=443, wallet="DUMMY-NOT-A-WALLET",
            worker="STAGING", threads=1, priority=2, tls_mode="auto",
        )
        manager = MinerManager(config)
        controller = Controller(manager, state_store=state, poll_interval=0.02)
        shutdown = threading.Timer(0.2, controller.request_shutdown)
        shutdown.start()
        try:
            with patch.object(manager, "start",
                              side_effect=AssertionError("First beta boot attempted to start miner")):
                result = controller.run()
        finally:
            shutdown.join(timeout=2)
        assert result == 0
        assert manager.pid is None
        assert state.load() is False
        print("PASS: Fresh independent beta defaults OFF; XMRig never starts")


if __name__ == "__main__":
    run()
