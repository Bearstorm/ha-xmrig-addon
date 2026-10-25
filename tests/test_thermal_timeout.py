"""Deterministic timeout regression tests for both thermal guards (offline)."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ("xmrig_haos_beta", "xmrig_haos_thermal_test")
NOW = 1790000000.0

class ThermalTimeoutTests(unittest.TestCase):
    def test_timeout_boundaries_and_fail_closed(self):
        for addon in ADDONS:
            with self.subTest(addon=addon):
                spec = importlib.util.spec_from_file_location(
                    "thermal_" + addon, ROOT / addon / "rootfs/app/thermal.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                with tempfile.TemporaryDirectory() as d:
                    options = Path(d) / "options.json"
                    options.write_text(json.dumps({
                        "thermal_protection_enabled": True,
                        "thermal_sensor_entity": "sensor.cpu",
                        "thermal_limit": 80,
                        "thermal_sensor_timeout": 180,
                        "thermal_notifications": False
                    }))
                    guard = mod.ThermalGuard(str(options))
                    guard.token = "TEST"
                    def check_age(age, *, field="last_reported"):
                        payload = {"state": "70", "attributes": {"unit_of_measurement": "°C"}}
                        if field:
                            payload[field] = datetime.fromtimestamp(
                                NOW - age, timezone.utc).isoformat()
                        guard.api = lambda endpoint: payload
                        with patch.object(mod.time, "time", return_value=NOW):
                            return guard.check()
                    self.assertEqual(check_age(0)[1], "ok")
                    self.assertEqual(check_age(180)[1], "ok")
                    self.assertEqual(check_age(181)[1], "stale_sensor")
                    self.assertEqual(check_age(-30)[1], "ok")
                    self.assertEqual(check_age(-31)[1], "stale_sensor")
                    self.assertEqual(check_age(10, field=None)[1], "missing_last_reported")
                    self.assertEqual(check_age(10, field="last_updated")[1], "missing_last_reported")
                    guard.api = lambda endpoint: (_ for _ in ()).throw(OSError("API down"))
                    self.assertEqual(guard.check()[1], "sensor_unavailable")

if __name__ == "__main__":
    unittest.main()
