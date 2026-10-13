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
for name in ("config", "miner_manager", "xmrig_monitor", "main"):
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
MinerSnapshot = sys.modules[f"{PACKAGE}.xmrig_monitor"].MinerSnapshot
MinerState = manager_module.MinerState
MinerError = manager_module.MinerError


class FakeManager:
    def __init__(self, states=None, *, start_result=True):
        self.states = iter(states or [MinerState.RUNNING])
        self.state = MinerState.STOPPED
        self.pid = 4321
        self.desired_running = True
        self.retry_at = None
        self.last_error = None
        self.start_calls = 0
        self.shutdown_calls = 0
        self.stop_calls = 0
        self.start_result = start_result
        self.start_exception = None
        self.reconcile_exception = None
        self.shutdown_exception = None
        self.on_reconcile = None

    def start(self):
        self.start_calls += 1
        if self.start_exception:
            raise self.start_exception
        if self.start_result and self.start_calls > 1:
            self.desired_running = True
            self.pid = 4321
            self.state = MinerState.RUNNING
        return self.start_result

    def reconcile(self):
        if self.reconcile_exception:
            raise self.reconcile_exception
        self.state = next(self.states, self.state)
        if self.state != MinerState.RUNNING:
            self.pid = None
        if self.on_reconcile:
            self.on_reconcile()
        return self.state

    def stop(self, timeout=10.0):
        self.stop_calls += 1
        self.desired_running = False
        self.pid = None
        self.state = MinerState.STOPPED

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


class FakeMonitor:
    def __init__(self, result=None):
        self.result = result or MinerSnapshot(True, hashrate_10s=123.0)
        self.calls = 0
        self.started = threading.Event()
        self.proceed = threading.Event()
        self.block = False
        self.raise_error = False

    def poll(self):
        self.calls += 1
        self.started.set()
        if self.block:
            self.proceed.wait(1.0)
        if self.raise_error:
            raise RuntimeError("secret from API")
        return self.result


class MonitoringControllerTests(unittest.TestCase):
    def test_no_monitor_keeps_existing_flow(self):
        manager = FakeManager()
        stop = threading.Event()
        manager.on_reconcile = stop.set
        controller = Controller(manager, stop_event=stop, poll_interval=0.001)
        self.assertEqual(controller.run(), 0)
        self.assertFalse(controller.snapshot.api_available)

    def test_monitor_reads_running_miner(self):
        manager = FakeManager()
        monitor = FakeMonitor()
        controller = Controller(manager, monitor=monitor, poll_interval=0.001)
        seen = []
        def done():
            if controller.snapshot.api_available:
                seen.append(controller.snapshot.hashrate_10s)
                controller.request_shutdown()
        manager.on_reconcile = done
        self.assertEqual(controller.run(), 0)
        self.assertEqual(seen, [123.0])
        self.assertGreaterEqual(monitor.calls, 1)

    def test_api_unavailable_does_not_stop_mining(self):
        manager = FakeManager()
        monitor = FakeMonitor(MinerSnapshot(False, error="api_unavailable"))
        controller = Controller(manager, monitor=monitor, poll_interval=0.001)
        def done():
            if monitor.started.is_set():
                controller.request_shutdown()
        manager.on_reconcile = done
        self.assertEqual(controller.run(), 0)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_monitor_exception_does_not_stop_mining(self):
        manager = FakeManager()
        monitor = FakeMonitor()
        monitor.raise_error = True
        controller = Controller(manager, monitor=monitor, poll_interval=0.001)
        def done():
            if monitor.started.is_set():
                controller.request_shutdown()
        manager.on_reconcile = done
        self.assertEqual(controller.run(), 0)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_late_response_after_process_exit_is_discarded(self):
        manager = FakeManager(states=[MinerState.RUNNING, MinerState.ERROR])
        manager.desired_running = True
        manager.retry_at = 10000.0
        monitor = FakeMonitor()
        monitor.block = True
        controller = Controller(manager, monitor=monitor, poll_interval=0.001)
        counter = [0]
        def done():
            counter[0] += 1
            if counter[0] == 1:
                monitor.started.wait(0.5)
            if counter[0] >= 2:
                monitor.proceed.set()
                controller.request_shutdown()
        manager.on_reconcile = done
        self.assertEqual(controller.run(), 0)
        self.assertFalse(controller.snapshot.api_available)
        self.assertEqual(controller.snapshot.error, "miner_not_running")

    def test_invalid_monitor_interval(self):
        with self.assertRaises(ValueError):
            Controller(FakeManager(), monitor_interval=0)

    def test_main_factory_failure_is_handled(self):
        self.assertEqual(controller_module.main(
            config_loader=lambda: object(),
            manager_factory=lambda config: (_ for _ in ()).throw(ValueError("bad")),
            install_signals=False,
        ), 1)

    def test_main_monitor_factory_failure_is_optional(self):
        manager = FakeManager(states=[MinerState.ERROR])
        manager.desired_running = False
        self.assertEqual(controller_module.main(
            config_loader=lambda: object(),
            manager_factory=lambda config: manager,
            monitor_factory=lambda: (_ for _ in ()).throw(ValueError("no api")),
            install_signals=False,
        ), 1)
        self.assertEqual(manager.shutdown_calls, 1)



class FakePublisher:
    def __init__(self, *, fail_start=False, fail_publish=False, fail_close=False):
        self.fail_start = fail_start
        self.fail_publish = fail_publish
        self.fail_close = fail_close
        self.started = 0
        self.closed = 0
        self.records = []
        self.published = threading.Event()
        self.commands = None

    def start(self):
        self.started += 1
        if self.fail_start:
            raise RuntimeError("broker failed")
        return True

    def publish(self, snapshot, *, process_running):
        self.records.append((snapshot, process_running))
        self.published.set()
        if self.fail_publish:
            raise RuntimeError("broker disconnected")
        return True

    def close(self):
        self.closed += 1
        if self.fail_close:
            raise RuntimeError("broker shutdown failed")


class MqttControllerTests(unittest.TestCase):
    def test_off_command_stops_without_killing_controller(self):
        from importlib import import_module
        import importlib.util
        spec = importlib.util.spec_from_file_location("controller_command_mailbox", APP_DIR / "mqtt_commands.py")
        cmd_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cmd_mod)
        manager = FakeManager(states=[MinerState.RUNNING, MinerState.STOPPED])
        publisher = FakePublisher()
        publisher.commands = cmd_mod.CommandMailbox()
        controller = Controller(manager, publisher=publisher, poll_interval=0.001)
        count = [0]
        def callback():
            count[0] += 1
            if count[0] == 1:
                publisher.commands.submit("xmrig_haos/command", b"OFF")
            if count[0] >= 3:
                controller.request_shutdown()
        manager.on_reconcile = callback
        self.assertEqual(controller.run(), 0)
        self.assertEqual(manager.stop_calls, 1)
        self.assertEqual(manager.start_calls, 1)

    def test_on_after_off_restarts_once(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("controller_command_mailbox_two", APP_DIR / "mqtt_commands.py")
        cmd_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cmd_mod)
        manager = FakeManager()
        publisher = FakePublisher()
        publisher.commands = cmd_mod.CommandMailbox()
        controller = Controller(manager, publisher=publisher, poll_interval=0.001)
        count = [0]
        def callback():
            count[0] += 1
            if count[0] == 1:
                publisher.commands.submit("xmrig_haos/command", b"OFF")
            elif count[0] == 2:
                publisher.commands.submit("xmrig_haos/command", b"ON")
            elif count[0] >= 4:
                controller.request_shutdown()
        manager.on_reconcile = callback
        self.assertEqual(controller.run(), 0)
        self.assertEqual(manager.stop_calls, 1)
        self.assertEqual(manager.start_calls, 2)

    def test_mqtt_is_optional(self):
        manager = FakeManager()
        stop = threading.Event()
        manager.on_reconcile = stop.set
        self.assertEqual(Controller(manager, stop_event=stop).run(), 0)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_publishes_snapshot_from_monitor_thread(self):
        manager = FakeManager()
        monitor = FakeMonitor()
        publisher = FakePublisher()
        controller = Controller(manager, monitor=monitor, publisher=publisher,
                                poll_interval=0.001, monitor_interval=0.01)
        def done():
            if publisher.published.is_set():
                controller.request_shutdown()
        manager.on_reconcile = done
        self.assertEqual(controller.run(), 0)
        self.assertEqual(publisher.started, 1)
        self.assertEqual(publisher.closed, 1)
        self.assertTrue(publisher.records[0][1])
        self.assertEqual(publisher.records[0][0].hashrate_10s, 123.0)

    def test_publish_exception_does_not_stop_miner(self):
        manager = FakeManager()
        publisher = FakePublisher(fail_publish=True)
        controller = Controller(manager, monitor=FakeMonitor(), publisher=publisher,
                                poll_interval=0.001, monitor_interval=0.01)
        manager.on_reconcile = lambda: publisher.published.is_set() and controller.request_shutdown()
        self.assertEqual(controller.run(), 0)
        self.assertGreaterEqual(len(publisher.records), 1)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_start_exception_does_not_stop_miner(self):
        manager = FakeManager()
        publisher = FakePublisher(fail_start=True)
        stop = threading.Event()
        manager.on_reconcile = stop.set
        self.assertEqual(Controller(manager, stop_event=stop, publisher=publisher).run(), 0)
        self.assertEqual(manager.shutdown_calls, 1)
        self.assertEqual(publisher.closed, 1)

    def test_close_exception_does_not_stop_miner(self):
        manager = FakeManager()
        publisher = FakePublisher(fail_close=True)
        stop = threading.Event()
        manager.on_reconcile = stop.set
        self.assertEqual(Controller(manager, stop_event=stop, publisher=publisher).run(), 0)
        self.assertEqual(manager.shutdown_calls, 1)

    def test_late_api_response_never_published(self):
        manager = FakeManager(states=[MinerState.RUNNING, MinerState.ERROR])
        manager.retry_at = 10000.0
        monitor = FakeMonitor()
        monitor.block = True
        publisher = FakePublisher()
        controller = Controller(manager, monitor=monitor, publisher=publisher,
                                poll_interval=0.001)
        calls = [0]
        def done():
            calls[0] += 1
            if calls[0] == 1:
                monitor.started.wait(0.5)
            if calls[0] >= 2:
                monitor.proceed.set()
                controller.request_shutdown()
        manager.on_reconcile = done
        self.assertEqual(controller.run(), 0)
        self.assertFalse(any(running for _, running in publisher.records))


if __name__ == "__main__":
    unittest.main(verbosity=2)
