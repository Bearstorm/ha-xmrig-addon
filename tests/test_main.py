"""Isolated tests for the main XMRig Python controller."""

from __future__ import annotations

import importlib.util
import sys
import threading
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "xmrig_haos" / "rootfs" / "app"
PACKAGE = "xmrig_controller_test_app"

# Load real project modules as a package without requiring __init__.py.
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(APP_DIR)]
sys.modules[PACKAGE] = pkg
for name in ("config", "miner_manager", "main"):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{name}", APP_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

controller_module = sys.modules[f"{PACKAGE}.main"]
manager_module = sys.modules[f"{PACKAGE}.miner_manager"]
config_module = sys.modules[f"{PACKAGE}.config"]
Controller = controller_module.Controller
MinerState = manager_module.MinerState
MinerError = manager_module.MinerError


class FakeManager:
    def __init__(self, states=None, *, start_result=True):
        self.states = iter(states or [MinerState.RUNNING])
        self.state = MinerState.STOPPED
        self.desired_running = True
        self.retry_at = None
        self.last_error = None
        self.start_calls = 0
        self.shutdown_calls = 0
        self.start_result = start_result
        self.start_exception = None
        self.reconcile_exception = None
        self.shutdown_exception = None
        self.on_reconcile = None

    def start(self):
        self.start_calls += 1
        if self.start_exception:
            raise self.start_exception
        return self.start_result

    def reconcile(self):
        if self.reconcile_exception:
            raise self.reconcile_exception
        self.state = next(self.states, self.state)
        if self.on_reconcile:
            self.on_reconcile()
        return self.state

    def shutdown(self, timeout=10.0):
        self.shutdown_calls += 1
        if self.shutdown_exception:
            raise self.shutdown_exception


class ControllerTests(unittest.TestCase):
    def test_starts_and_stops_on_request(self):
        manager = FakeManager()
        stop = threading.Event()
        manager.on_reconcile = stop.set
        self.assertEqual(Controller(manager, stop_event=stop).run(), 0)
        self.assertEqual(manager.start_calls, 1)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_request_shutdown_sets_event(self):
        manager = FakeManager()
        stop = threading.Event()
        controller = Controller(manager, stop_event=stop)
        controller.request_shutdown()
        self.assertTrue(stop.is_set())
        self.assertEqual(controller.run(), 0)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_invalid_poll_interval(self):
        with self.assertRaises(ValueError):
            Controller(FakeManager(), poll_interval=0)

    def test_negative_poll_interval(self):
        with self.assertRaises(ValueError):
            Controller(FakeManager(), poll_interval=-1)

    def test_fatal_error_exits_with_failure(self):
        manager = FakeManager(states=[MinerState.ERROR])
        manager.desired_running = False
        self.assertEqual(Controller(manager).run(), 1)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_retry_pending_does_not_quit(self):
        manager = FakeManager(states=[MinerState.ERROR, MinerState.RUNNING])
        manager.retry_at = 123.0
        stop = threading.Event()
        calls = [0]
        def on_reconcile():
            calls[0] += 1
            if calls[0] == 2:
                stop.set()
        manager.on_reconcile = on_reconcile
        self.assertEqual(Controller(manager, stop_event=stop, poll_interval=0.001).run(), 0)
        self.assertEqual(calls[0], 2)

    def test_manager_start_failure_always_shuts_down(self):
        manager = FakeManager()
        manager.start_exception = MinerError("private")
        self.assertEqual(Controller(manager).run(), 1)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_reconcile_failure_always_shuts_down(self):
        manager = FakeManager()
        manager.reconcile_exception = MinerError("private")
        self.assertEqual(Controller(manager).run(), 1)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_shutdown_failure_returns_failure(self):
        manager = FakeManager()
        stop = threading.Event()
        stop.set()
        manager.shutdown_exception = MinerError("private")
        self.assertEqual(Controller(manager, stop_event=stop).run(), 1)

    def test_main_bad_configuration(self):
        def invalid_config():
            raise config_module.ConfigError("secret")
        self.assertEqual(controller_module.main(config_loader=invalid_config, install_signals=False), 1)

    def test_main_wires_dependencies(self):
        fake = FakeManager(states=[MinerState.ERROR])
        fake.desired_running = False
        marker = object()
        received = []
        self.assertEqual(controller_module.main(
            config_loader=lambda: marker,
            manager_factory=lambda config: (received.append(config), fake)[1],
            install_signals=False,
        ), 1)
        self.assertIs(received[0], marker)
        self.assertEqual(fake.shutdown_calls, 1)

    def test_no_mqtt_dependency(self):
        source = (APP_DIR / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("import paho", source)
        self.assertNotIn("import mqtt", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
