"""Offline tests for strict, bounded MQTT command processing."""
import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "xmrig_haos/rootfs/app/mqtt_commands.py"
spec = importlib.util.spec_from_file_location("xmrig_commands_test_module", PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class CommandMailboxTests(unittest.TestCase):
    def setUp(self):
        self.box = module.CommandMailbox()

    def test_on(self):
        self.assertTrue(self.box.submit("xmrig_haos/command", b"ON"))
        self.assertEqual(self.box.take(), "ON")

    def test_off(self):
        self.assertTrue(self.box.submit("xmrig_haos/command", b"OFF"))
        self.assertEqual(self.box.take(), "OFF")

    def test_reject_retained(self):
        self.assertFalse(self.box.submit("xmrig_haos/command", b"ON", retained=True))
        self.assertIsNone(self.box.take())

    def test_reject_unknown_topic(self):
        self.assertFalse(self.box.submit("xmrig_haos/other", b"OFF"))
        self.assertIsNone(self.box.take())

    def test_reject_fuzzy_commands(self):
        for payload in (b"on", b"STOP", b"ON\n", b"1", b"", b"OFF "):
            with self.subTest(payload=payload):
                self.assertFalse(self.box.submit("xmrig_haos/command", payload))
        self.assertIsNone(self.box.take())

    def test_latest_state_wins(self):
        self.box.submit("xmrig_haos/command", b"ON")
        self.box.submit("xmrig_haos/command", b"OFF")
        self.assertEqual(self.box.take(), "OFF")

    def test_consume_exactly_once(self):
        self.box.submit("xmrig_haos/command", b"ON")
        self.assertEqual(self.box.take(), "ON")
        self.assertIsNone(self.box.take())

    def test_no_exceptions_for_invalid_payload_type(self):
        self.assertFalse(self.box.submit("xmrig_haos/command", "ON"))
        self.assertFalse(self.box.submit("xmrig_haos/command", None))


if __name__ == "__main__":
    unittest.main()
