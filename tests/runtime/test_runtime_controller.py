"""Isolated subprocess integration tests: never execute the actual XMRig binary.

Docker executes these tests with --network none and a read-only filesystem.
The miner manager is REAL; its binary is always an executable mock created in
an isolated temporary directory. MQTT and Supervisor are never contacted.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import MinerConfig
from app.main import Controller
from app.miner_manager import MinerManager, MinerState, RestartPolicy
from app.xmrig_monitor import MinerSnapshot

MOCK_SOURCE = '''#!/usr/bin/env python3
import json
import os
import signal
import sys
import time

log = os.environ["MOCK_XMRIG_LOG"]

def record(action):
    with open(log, "a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": action, "pid": os.getpid()}) + "\\n")
        stream.flush()

def terminate(signum, frame):
    record("terminated")
    raise SystemExit(0)

signal.signal(signal.SIGTERM, terminate)
record("started")
if os.environ.get("MOCK_XMRIG_CRASH") == "1":
    raise SystemExit(7)
while True:
    time.sleep(0.05)
'''


class OfflineMonitor:
    def __init__(self):
        self.calls = 0

    def poll(self):
        self.calls += 1
        return MinerSnapshot(False, error="api_unavailable")


class ControllerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xmrig-runtime-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mock_binary = self.root / "xmrig-mock"
        self.mock_binary.write_text(MOCK_SOURCE, encoding="utf-8")
        self.mock_binary.chmod(0o700)
        self.events_path = self.root / "events.jsonl"
        self.env = patch.dict(os.environ, {"MOCK_XMRIG_LOG": str(self.events_path)}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config = MinerConfig(
            pool="example.invalid", port=443, wallet="DUMMY-NOT-REAL",
            worker="TEST", threads=2, priority=2, tls_mode="auto",
        )
        self.managers = []
        self.addCleanup(self.cleanup_managers)

    def cleanup_managers(self):
        for manager in self.managers:
            manager.shutdown(timeout=1.0)

    def manager(self, policy=None):
        manager = MinerManager(
            self.config, binary=str(self.mock_binary),
            restart_policy=policy or RestartPolicy(delays=(0.05, 0.05), stable_seconds=60),
        )
        self.managers.append(manager)
        return manager

    def events(self):
        if not self.events_path.exists():
            return []
        return [json.loads(line) for line in self.events_path.read_text().splitlines() if line]

    def wait_for(self, predicate, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.01)
        return False

    def test_real_subprocess_starts_and_stops(self):
        manager = self.manager()
        self.assertTrue(manager.start())
        self.assertTrue(self.wait_for(lambda: len(self.events()) >= 1))
        self.assertEqual(manager.state, MinerState.RUNNING)
        self.assertIsNotNone(manager.pid)
        manager.shutdown(timeout=2.0)
        self.assertIsNone(manager.pid)
        self.assertEqual(manager.state, MinerState.STOPPED)
        self.assertTrue(self.wait_for(lambda: any(e["event"] == "terminated" for e in self.events())))

    def test_duplicate_start_does_not_spawn_another_process(self):
        manager = self.manager()
        self.assertTrue(manager.start())
        self.assertFalse(manager.start())
        self.assertTrue(self.wait_for(lambda: len(self.events()) >= 1))
        time.sleep(0.08)
        self.assertEqual(len([e for e in self.events() if e["event"] == "started"]), 1)

    def test_crash_retries_are_bounded(self):
        with patch.dict(os.environ, {"MOCK_XMRIG_CRASH": "1"}):
            manager = self.manager(RestartPolicy(delays=(0.03, 0.03), stable_seconds=60))
            manager.start()
            self.assertTrue(self.wait_for(lambda: self._reconcile_exhausted(manager)))
            self.assertEqual(manager.state, MinerState.ERROR)
            self.assertFalse(manager.desired_running)
            self.assertIsNone(manager.pid)
            self.assertEqual(len([e for e in self.events() if e["event"] == "started"]), 3)

    @staticmethod
    def _reconcile_exhausted(manager):
        manager.reconcile()
        return manager.state == MinerState.ERROR and not manager.desired_running

    def test_monitor_failure_does_not_stop_controller_miner(self):
        manager = self.manager()
        monitor = OfflineMonitor()
        stop = threading.Event()
        controller = Controller(manager, monitor=monitor, stop_event=stop,
                                poll_interval=0.02, monitor_interval=0.03)
        result = []
        worker = threading.Thread(target=lambda: result.append(controller.run()))
        worker.start()
        try:
            self.assertTrue(self.wait_for(lambda: monitor.calls > 0))
            self.assertTrue(self.wait_for(lambda: len(self.events()) > 0))
            self.assertTrue(worker.is_alive())
            self.assertEqual(manager.state, MinerState.RUNNING)
            self.assertFalse(controller.snapshot.api_available)
        finally:
            controller.request_shutdown()
            worker.join(timeout=4)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result, [0])
        self.assertIsNone(manager.pid)

    def test_controller_shutdown_reaps_real_child(self):
        manager = self.manager()
        stop = threading.Event()
        controller = Controller(manager, stop_event=stop, poll_interval=0.02)
        result = []
        worker = threading.Thread(target=lambda: result.append(controller.run()))
        worker.start()
        try:
            self.assertTrue(self.wait_for(lambda: any(e["event"] == "started" for e in self.events())))
            child_pid = manager.pid
            self.assertIsNotNone(child_pid)
        finally:
            controller.request_shutdown()
            worker.join(timeout=4)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result, [0])
        self.assertEqual(manager.state, MinerState.STOPPED)
        self.assertTrue(self.wait_for(lambda: any(e["event"] == "terminated" for e in self.events())))


if __name__ == "__main__":
    unittest.main(verbosity=2)
