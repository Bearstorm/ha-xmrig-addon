"""Offline tests for integrated beta thermal protection (no real mining)."""
import json
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "xmrig_haos_beta" / "rootfs"))
from app.thermal import ThermalGuard
from app.main import Controller
from app.miner_manager import MinerState

class FakeResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return json.dumps(self.data).encode()

class FakeManager:
    def __init__(self):
        self.desired_running = True
        self.state = MinerState.RUNNING
        self.pid = 123
        self.stop_calls = 0
    def stop(self):
        self.stop_calls += 1
        self.desired_running = False
        self.state = MinerState.STOPPED

class ThermalTests(unittest.TestCase):
    def guard(self, **changes):
        opts = {"thermal_protection_enabled": True,
                "thermal_sensor_entity": "sensor.cpu",
                "thermal_limit": 80, "thermal_sensor_timeout": 180,
                "thermal_notifications": False}
        opts.update(changes)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "options.json"
        path.write_text(json.dumps(opts))
        guard = ThermalGuard(str(path))
        guard.token = "FAKE"
        return guard

    def check(self, value="70", age=10, unit="°C", reported=True):
        guard = self.guard()
        payload = {"state": value, "attributes": {"unit_of_measurement": unit}}
        if reported:
            payload["last_reported"] = (datetime.now(timezone.utc) -
                timedelta(seconds=age)).isoformat()
        with patch("app.thermal.urlopen", return_value=FakeResponse(payload)):
            return guard.check()

    def test_safe(self): self.assertEqual(self.check()[0], True)
    def test_hot(self): self.assertEqual(self.check("81")[1], "temperature_limit_exceeded")
    def test_equal_limit_allowed(self): self.assertEqual(self.check("80")[0], True)
    def test_stale(self): self.assertEqual(self.check(age=200)[1], "stale_sensor")
    def test_missing_report_fails_closed(self): self.assertEqual(self.check(reported=False)[1], "missing_last_reported")
    def test_unknown_fails_closed(self): self.assertFalse(self.check("unknown")[0])
    def test_wrong_unit_fails_closed(self): self.assertEqual(self.check(unit="°F")[1], "invalid_temperature_unit")
    def test_disabled_does_not_call_api(self):
        guard = self.guard(thermal_protection_enabled=False)
        with patch.object(guard, "api", side_effect=AssertionError("called")):
            self.assertTrue(guard.check()[0])
    def test_invalid_entity_rejected(self):
        with self.assertRaises(ValueError):
            self.guard(thermal_sensor_entity="switch.mining")
    def test_trip_stops_and_latches(self):
        guard = self.guard()
        guard.check = lambda: (False, "stale_sensor", 70)
        guard.notify = lambda *args: None
        manager = FakeManager()
        controller = Controller(manager, thermal_guard=guard)
        self.assertFalse(controller._thermal_check(force=True))
        self.assertEqual(manager.stop_calls, 1)
        self.assertFalse(controller._thermal_check(force=True))
        self.assertEqual(manager.stop_calls, 1)
    def test_safe_allows_start(self):
        guard = self.guard()
        guard.check = lambda: (True, "ok", 70)
        controller = Controller(FakeManager(), thermal_guard=guard)
        self.assertTrue(controller._thermal_check(force=True))

if __name__ == "__main__":
    unittest.main()
