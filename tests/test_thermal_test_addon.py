"""Validate isolated installable thermal test add-on without running mining."""
import json
import sys
import unittest
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "xmrig_haos_thermal_test"
class IsolationTests(unittest.TestCase):
    def test_addon_manifest_and_defaults(self):
        cfg = yaml.safe_load((ADDON / "config.yaml").read_text())
        beta = yaml.safe_load((ROOT / "xmrig_haos_beta/config.yaml").read_text())
        self.assertEqual(cfg["slug"], "xmrig_haos_thermal_test")
        self.assertNotEqual(cfg["slug"], beta["slug"])
        self.assertEqual(cfg["boot"], "manual")
        self.assertFalse(cfg["full_access"])
        self.assertFalse(cfg["host_network"])
        self.assertTrue(cfg["homeassistant_api"])
        self.assertFalse(cfg["options"]["thermal_protection_enabled"])
        self.assertEqual(cfg["options"]["thermal_limit"], 80)
        self.assertEqual(cfg["options"]["thermal_sensor_timeout"], 180)
        self.assertEqual(set(cfg["options"]), set(cfg["schema"]))
    def test_mqtt_topics_and_ids_are_isolated(self):
        sys.path.insert(0, str(ADDON / "rootfs"))
        from app.mqtt_discovery import DiscoveryPayloads
        from app.mqtt_commands import CommandMailbox
        d = DiscoveryPayloads()
        self.assertEqual(d.command_topic, "xmrig_haos_thermal_test/command")
        self.assertTrue(all("xmrig_haos_beta/" not in m.topic for m in d.discovery_messages()))
        self.assertTrue(all("xmrig_haos_thermal_test" in m.topic for m in d.discovery_messages()))
        inbox = CommandMailbox()
        self.assertFalse(inbox.submit("xmrig_haos_beta/command", b"ON"))
        self.assertTrue(inbox.submit("xmrig_haos_thermal_test/command", b"OFF"))
    def test_python_compiles(self):
        import ast
        for p in (ADDON / "rootfs/app").glob("*.py"):
            ast.parse(p.read_text(), filename=str(p))
if __name__ == "__main__": unittest.main()
