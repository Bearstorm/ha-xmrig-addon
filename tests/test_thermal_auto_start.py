"""First-install auto-start policy; no real miner or network."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "xmrig_haos_thermal_test/rootfs"))
from app.main import Controller
from app.miner_manager import MinerState
from app.mining_state import MiningStateStore
from app.thermal import ThermalGuard

class AutoStartTests(unittest.TestCase):
    def make(self, mode="automatic", thermal=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        folder = Path(directory.name)
        opts = folder / "options.json"
        opts.write_text(json.dumps({
            "mining_start_mode": mode,
            "thermal_protection_enabled": thermal,
            "thermal_sensor_entity": "sensor.cpu",
            "thermal_limit": 80, "thermal_sensor_timeout": 180,
            "thermal_notifications": False
        }))
        guard = ThermalGuard(str(opts))
        store = MiningStateStore(folder / "mining.json")
        manager = Mock()
        manager.state = MinerState.STOPPED
        manager.pid = None
        manager.desired_running = False
        manager.retry_at = None
        manager.start.side_effect = lambda: setattr(manager, "desired_running", True)
        manager.reconcile.side_effect = lambda: MinerState.STOPPED
        manager.shutdown.side_effect = lambda: None
        controller = Controller(manager, state_store=store, thermal_guard=guard,
                                auto_start=guard.start_mode == "automatic")
        controller._stop_event.wait = lambda seconds: controller.request_shutdown()
        return controller, manager, store, guard

    def test_fresh_install_automatic_starts(self):
        controller, manager, store, _ = self.make()
        controller.run()
        manager.start.assert_called_once()
        self.assertTrue(store.load())

    def test_fresh_install_manual_stays_off(self):
        controller, manager, store, _ = self.make(mode="manual")
        controller.run()
        manager.start.assert_not_called()
        self.assertFalse(store.load())

    def test_manual_does_not_resume_saved_on(self):
        controller, manager, store, _ = self.make(mode="manual")
        store.save(True)
        controller.run()
        manager.start.assert_not_called()
        self.assertFalse(store.load())

    def test_manual_to_automatic_transition(self):
        controller, manager, store, _ = self.make(mode="manual")
        store.save(True)
        controller.run()
        self.assertTrue(store.manual_pending())
        next_controller, next_manager, _, _ = self.make()
        next_controller._state_store = store
        next_controller.run()
        next_manager.start.assert_called_once()
        self.assertFalse(store.manual_pending())

    def test_legacy_saved_off_manual_to_auto(self):
        # Regression: .3/.4 may have already stored OFF before mode changes.
        controller, manager, store, _ = self.make(mode="manual")
        store.save(False)
        controller.run()
        manager.start.assert_not_called()
        self.assertTrue(store.manual_pending())
        next_controller, next_manager, _, _ = self.make()
        next_controller._state_store = store
        next_controller.run()
        next_manager.start.assert_called_once()
        self.assertFalse(store.manual_pending())

    def test_legacy_saved_off_thermal_latch_blocks_auto(self):
        controller, manager, store, _ = self.make(mode="manual")
        store.save(False)
        store.mark_thermal()
        controller.run()
        self.assertTrue(store.manual_pending())
        next_controller, next_manager, _, _ = self.make()
        next_controller._state_store = store
        next_controller.run()
        next_manager.start.assert_not_called()
        self.assertTrue(store.thermal_tripped())

    def test_thermal_marker_blocks_auto_after_manual(self):
        controller, manager, store, _ = self.make(mode="manual")
        store.save(True)
        store.mark_thermal()
        controller.run()
        next_controller, next_manager, _, _ = self.make()
        next_controller._state_store = store
        next_controller.run()
        next_manager.start.assert_not_called()
        self.assertTrue(store.thermal_tripped())

    def test_saved_off_overrides_automatic(self):
        controller, manager, store, _ = self.make()
        store.save(False)
        controller.run()
        manager.start.assert_not_called()
        self.assertFalse(store.load())

    def test_thermal_trip_stays_off(self):
        controller, manager, store, guard = self.make(thermal=True)
        guard.check = lambda: (False, "temperature_limit_exceeded", 85)
        controller.run()
        manager.start.assert_not_called()
        self.assertFalse(store.load())

    def test_unclean_shutdown_guard_blocks_auto(self):
        controller, manager, store, _ = self.make()
        store.arm()
        controller.run()
        manager.start.assert_not_called()
        self.assertTrue(store.guard_exists())

    def test_invalid_start_mode_rejected(self):
        with self.assertRaises(ValueError):
            self.make(mode="surprise")

if __name__ == "__main__":
    unittest.main()
