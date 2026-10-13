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
from app.mining_state import MiningStateStore, StateStoreError
from app.mqtt_commands import CommandMailbox
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



class StubPublisher:
    def __init__(self):
        self.commands = CommandMailbox()
        self.records = []

    def start(self):
        return True

    def publish(self, snapshot, *, process_running):
        self.records.append((snapshot, process_running))
        return True

    def close(self):
        pass


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


    def _run_controller_thread(self, manager, store, publisher=None):
        controller = Controller(
            manager, state_store=store, publisher=publisher,
            poll_interval=0.02, monitor_interval=0.03,
        )
        result = []
        thread = threading.Thread(target=lambda: result.append(controller.run()))
        thread.start()
        return controller, thread, result

    def test_off_persists_across_actual_controller_restart(self):
        store = MiningStateStore(self.root / "xmrig_state.json")
        first = self.manager()
        pub = StubPublisher()
        controller, thread, result = self._run_controller_thread(first, store, pub)
        try:
            self.assertTrue(self.wait_for(lambda: any(e["event"] == "started" for e in self.events())))
            pub.commands.submit("xmrig_haos/command", b"OFF")
            self.assertTrue(self.wait_for(lambda: not first.desired_running and first.pid is None))
            self.assertFalse(store.load())
            self.assertEqual(first.state, MinerState.STOPPED)
        finally:
            controller.request_shutdown()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [0])
        initial_count = len([e for e in self.events() if e["event"] == "started"])

        second = self.manager()
        second_pub = StubPublisher()
        controller2, thread2, result2 = self._run_controller_thread(second, store, second_pub)
        try:
            self.assertTrue(self.wait_for(lambda: bool(second_pub.records)))
            time.sleep(0.15)
            self.assertEqual(
                len([e for e in self.events() if e["event"] == "started"]),
                initial_count,
            )
            self.assertIsNone(second.pid)
            self.assertFalse(any(running for _, running in second_pub.records))
        finally:
            controller2.request_shutdown()
            thread2.join(timeout=5)
        self.assertFalse(thread2.is_alive())
        self.assertEqual(result2, [0])

    def test_corrupt_state_never_spawns_mock_process(self):
        store = MiningStateStore(self.root / "xmrig_state.json")
        store.path.write_text("corrupted")
        manager = self.manager()
        publisher = StubPublisher()
        controller, thread, result = self._run_controller_thread(manager, store, publisher)
        try:
            self.assertTrue(self.wait_for(lambda: len(publisher.records) >= 1))
            time.sleep(0.1)
            self.assertEqual(self.events(), [])
            self.assertIsNone(manager.pid)
        finally:
            controller.request_shutdown()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [0])

    def test_failed_on_persistence_blocks_process_start(self):
        class FailingStateStore:
            def load(self):
                return False
            def guard_exists(self):
                return False
            def arm(self):
                pass
            def save(self, running):
                raise StateStoreError("simulated disk failure")
            def disarm(self):
                pass

        manager = self.manager()
        pub = StubPublisher()
        controller, thread, result = self._run_controller_thread(manager, FailingStateStore(), pub)
        try:
            self.assertTrue(self.wait_for(lambda: bool(pub.records)))
            pub.commands.submit("xmrig_haos/command", b"ON")
            time.sleep(0.2)
            self.assertEqual(self.events(), [])
            self.assertIsNone(manager.pid)
        finally:
            controller.request_shutdown()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [0])

    def test_failed_off_write_retains_guard_across_restart(self):
        store = MiningStateStore(self.root / "xmrig_state.json")
        manager = self.manager()
        pub = StubPublisher()
        controller, worker, results = self._run_controller_thread(manager, store, pub)
        try:
            self.assertTrue(self.wait_for(lambda: manager.pid is not None))
            self.assertTrue(store.guard_exists())
            original_save = store.save
            def failing_off(running):
                if not running:
                    raise StateStoreError("simulated OFF disk failure")
                return original_save(running)
            with patch.object(store, "save", side_effect=failing_off):
                pub.commands.submit("xmrig_haos/command", b"OFF")
                self.assertTrue(self.wait_for(
                    lambda: not manager.desired_running and manager.pid is None
                ))
                self.assertTrue(store.guard_exists())
        finally:
            controller.request_shutdown()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results, [0])
        self.assertTrue(store.guard_exists())

        second = self.manager()
        controller2, worker2, results2 = self._run_controller_thread(second, store, StubPublisher())
        try:
            time.sleep(0.2)
            self.assertIsNone(second.pid)
            self.assertEqual(second.state, MinerState.STOPPED)
        finally:
            controller2.request_shutdown()
            worker2.join(timeout=5)
        self.assertEqual(results2, [0])

    def test_graceful_on_restart_allows_autostart(self):
        store = MiningStateStore(self.root / "xmrig_state.json")
        store.save(True)
        first = self.manager()
        controller, worker, results = self._run_controller_thread(first, store)
        try:
            self.assertTrue(self.wait_for(lambda: first.pid is not None))
        finally:
            controller.request_shutdown()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results, [0])
        self.assertFalse(store.guard_exists())
        second = self.manager()
        controller2, worker2, results2 = self._run_controller_thread(second, store)
        try:
            self.assertTrue(self.wait_for(lambda: second.pid is not None))
        finally:
            controller2.request_shutdown()
            worker2.join(timeout=5)
        self.assertFalse(worker2.is_alive())
        self.assertEqual(results2, [0])

    def test_off_command_cancels_crash_retries(self):
        with patch.dict(os.environ, {"MOCK_XMRIG_CRASH": "1"}):
            store = MiningStateStore(self.root / "xmrig_state.json")
            manager = self.manager(RestartPolicy(delays=(0.5, 0.5), stable_seconds=60))
            pub = StubPublisher()
            controller, thread, result = self._run_controller_thread(manager, store, pub)
            try:
                self.assertTrue(self.wait_for(
                    lambda: manager.state == MinerState.ERROR and manager.retry_at is not None
                ))
                pub.commands.submit("xmrig_haos/command", b"OFF")
                self.assertTrue(self.wait_for(
                    lambda: not manager.desired_running and manager.retry_at is None
                ))
                time.sleep(0.6)
                self.assertEqual(len([e for e in self.events() if e["event"] == "started"]), 1)
                self.assertFalse(store.load())
            finally:
                controller.request_shutdown()
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result, [0])


    def test_controller_exhaustion_returns_error_and_reaps_child(self):
        with patch.dict(os.environ, {"MOCK_XMRIG_CRASH": "1"}):
            store = MiningStateStore(self.root / "state.json")
            manager = self.manager(RestartPolicy(delays=(0.03, 0.03), stable_seconds=60))
            controller = Controller(manager, state_store=store, poll_interval=0.02)
            self.assertEqual(controller.run(), 1)
            self.assertFalse(manager.desired_running)
            self.assertIsNone(manager.pid)
            self.assertTrue(store.guard_exists())
            self.assertEqual(
                len([e for e in self.events() if e["event"] == "started"]), 3
            )

    def test_queued_on_is_ignored_when_shutdown_requested(self):
        store = MiningStateStore(self.root / "state.json")
        store.save(False)
        manager = self.manager()
        publisher = StubPublisher()
        self.assertTrue(publisher.commands.submit("xmrig_haos/command", b"ON"))
        controller = Controller(manager, publisher=publisher,
                                state_store=store, poll_interval=0.02)
        controller.request_shutdown()
        self.assertEqual(controller.run(), 0)
        self.assertEqual(self.events(), [])
        self.assertIsNone(manager.pid)
        self.assertFalse(store.load())

    def test_off_after_exhaustion_stops_and_saves_state(self):
        store = MiningStateStore(self.root / "state.json")
        store.save(True)
        with patch.dict(os.environ, {"MOCK_XMRIG_CRASH": "1"}):
            manager = self.manager(RestartPolicy(delays=(0.03, 0.03), stable_seconds=60))
            controller = Controller(manager, state_store=store, poll_interval=0.02)
            self.assertEqual(controller.run(), 1)
        self.assertTrue(store.guard_exists())
        publisher = StubPublisher()
        controller2 = Controller(manager, state_store=store, publisher=publisher,
                                 poll_interval=0.02)
        self.assertTrue(publisher.commands.submit("xmrig_haos/command", b"OFF"))
        controller2._apply_mqtt_command()
        self.assertFalse(store.load())
        self.assertFalse(store.guard_exists())
        self.assertFalse(manager.desired_running)



if __name__ == "__main__":
    unittest.main(verbosity=2)
