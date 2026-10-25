"""Smoke-test the real beta main() wiring and /data/options.json contract.

Runs inside the independently built beta image, with an isolated writable /data
tmpfs, no network and a hard failure if the actual miner would be spawned.
No real Home Assistant, Supervisor token or mining process is used.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

from app import main as beta_main
from app.config import load_config
from app.miner_manager import MinerManager
from app.mining_state import MiningStateStore

DATA = Path("/data")
OPTIONS = DATA / "options.json"
STATE = DATA / "xmrig_state.json"


def write_options(wallet: str = "STAGING-TEST-IDENTIFIER") -> None:
    OPTIONS.write_text(
        json.dumps({
            "pool": "example.invalid",
            "port": 443,
            "wallet": wallet,
            "worker": "STAGING",
            "threads": 1,
            "priority": 2,
            "tls_mode": "auto",
            "mining_start_mode": "manual",
        }),
        encoding="utf-8",
    )


def protected_manager(config):
    manager = MinerManager(config)
    def never_start():
        raise AssertionError("TEST FAILED: beta attempted to start XMRig")
    manager.start = never_start
    return manager


def run_off_boot(description: str) -> None:
    # main() creates the real Controller; give the run a bounded shutdown.
    original_cls = beta_main.Controller

    class TimedController(original_cls):
        def run(self):
            timer = threading.Timer(0.25, self.request_shutdown)
            timer.start()
            try:
                return super().run()
            finally:
                timer.cancel()
                timer.join(timeout=2)

    with patch.object(beta_main, "Controller", TimedController):
        result = beta_main.main(
            config_loader=load_config,
            manager_factory=protected_manager,
            monitor_factory=lambda: None,
            publisher_factory=lambda: None,
            state_store_factory=MiningStateStore,
            install_signals=False,
        )
    assert result == 0, f"{description}: Controller result {result}"
    print("PASS: " + description)


def run() -> None:
    assert DATA.is_dir(), "Test requires a separate writable /data mount"
    write_options()
    assert not STATE.exists(), "Fresh staging test must not share existing state"
    assert MiningStateStore().load() is False
    run_off_boot("real main() fresh /data/options.json starts safely OFF")
    assert not STATE.exists(), "First OFF boot must not persist ON"

    store = MiningStateStore()
    store.save(True)
    store.arm()
    run_off_boot("real main() rejects crash marker despite stored ON")
    assert store.guard_exists(), "Crash guard must remain armed"

    OPTIONS.write_text("{ broken", encoding="utf-8")
    result = beta_main.main(
        manager_factory=protected_manager,
        monitor_factory=lambda: None,
        publisher_factory=lambda: None,
        state_store_factory=MiningStateStore,
        install_signals=False,
    )
    assert result == 1, "Broken options.json must block Controller launch"
    print("PASS: invalid Supervisor options.json fails safely")

    write_options(wallet="")
    result = beta_main.main(
        manager_factory=protected_manager,
        monitor_factory=lambda: None,
        publisher_factory=lambda: None,
        state_store_factory=MiningStateStore,
        install_signals=False,
    )
    assert result == 1, "Empty wallet must block Controller launch"
    print("PASS: empty beta wallet rejects mining configuration")


if __name__ == "__main__":
    run()
