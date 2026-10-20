"""Beta state recovery matrix: missing, malformed and invalid guard all fail OFF.

Every attempted miner launch fails this test. Network and actual XMRig unused.
"""
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from app.config import MinerConfig
from app.main import Controller
from app.miner_manager import MinerManager
from app.mining_state import MiningStateStore, StateStoreError

CONFIG = MinerConfig(pool="example.invalid",port=443,wallet="FAKE-CI",
                     worker="TEST",threads=1,priority=2,tls_mode="auto")


def no_mining_run(store):
    manager = MinerManager(CONFIG)
    control = Controller(manager, state_store=store, poll_interval=.02)
    timer = threading.Timer(.15, control.request_shutdown)
    timer.start()
    try:
        with patch.object(manager, "start", side_effect=AssertionError("Unexpected miner start")):
            assert control.run() == 0
    finally:
        timer.join(timeout=2)
    assert manager.pid is None


def run():
    with tempfile.TemporaryDirectory(prefix="beta-state-recovery-") as directory:
        root=Path(directory)
        store=MiningStateStore(root/"state.json")
        no_mining_run(store)
        store.path.write_text("garbage",encoding="utf-8")
        no_mining_run(store)
        store.path.write_text(json.dumps({"version":1,"running":"true"}),encoding="utf-8")
        no_mining_run(store)
        store.path.write_text(json.dumps({"version":2,"running":True}),encoding="utf-8")
        no_mining_run(store)
        store.save(True)
        store.guard_path.write_text("tampered",encoding="utf-8")
        no_mining_run(store)
        store.guard_path.unlink()
        store.guard_path.mkdir()
        no_mining_run(store)
        store.guard_path.rmdir()
        store.arm()
        no_mining_run(store)
        assert store.guard_exists()
        store.save(False)
        store.disarm()
        no_mining_run(store)
        assert not store.guard_exists()
        assert store.load() is False
        print("PASS: beta damaged state / invalid or armed guard fails safely OFF")


if __name__=="__main__":
    run()
