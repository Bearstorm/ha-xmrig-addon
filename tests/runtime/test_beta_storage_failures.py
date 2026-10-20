"""Step 48: beta storage failures must never launch XMRig.

No real miner, MQTT service or live HAOS access. Run inside isolated beta image.
"""
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from app.config import MinerConfig
from app.main import Controller
from app.miner_manager import MinerManager
from app.mining_state import MiningStateStore, StateStoreError

CONFIG = MinerConfig(pool="example.invalid", port=443, wallet="CI-FAKE",
                     worker="CI", threads=1, priority=2, tls_mode="auto")


def drive(store, on_command=False):
    manager = MinerManager(CONFIG)
    class Stub:
        from app.mqtt_commands import CommandMailbox
        def __init__(self):
            self.commands = self.CommandMailbox()
        def start(self): return True
        def publish(self, *args, **kwargs): return True
        def close(self): pass
    pub = Stub()
    controller = Controller(manager, state_store=store, publisher=pub, poll_interval=.02)
    stop = threading.Timer(.2, controller.request_shutdown)
    if on_command:
        pub.commands.submit("xmrig_haos_beta/command", b"ON")
    stop.start()
    try:
        with patch.object(manager, "start", side_effect=AssertionError("Storage failure attempted mining")):
            assert controller.run() == 0
    finally:
        stop.join(timeout=3)
    assert manager.pid is None


def run():
    with tempfile.TemporaryDirectory(prefix="beta-storage-") as directory:
        root = Path(directory)
        missing = MiningStateStore(root / "missing" / "state.json")
        drive(missing)
        drive(missing, on_command=True)

        directory_as_file = root / "directory-as-state.json"
        directory_as_file.mkdir()
        drive(MiningStateStore(directory_as_file))

        state = MiningStateStore(root / "state.json")
        state.save(False)
        with patch.object(state, "arm", side_effect=StateStoreError("simulated storage write failure")):
            drive(state, on_command=True)
        assert not state.load()
        assert not state.guard_exists()

        state.save(True)
        with patch.object(state, "guard_exists", side_effect=StateStoreError("simulated unreadable guard")):
            drive(state)
        assert state.load()

        with patch.object(state, "load", side_effect=StateStoreError("simulated unreadable state")):
            drive(state)
        print("PASS: missing/unreadable /data and failed guard writes block mining")


if __name__ == "__main__":
    run()
