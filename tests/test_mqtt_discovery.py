"""Offline unit tests for XMRig MQTT Discovery messages; no broker needed."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "xmrig_haos" / "rootfs" / "app"
PACKAGE = "mqtt_discovery_test_pkg"
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(APP)]
sys.modules[PACKAGE] = pkg
for name in ("xmrig_monitor", "mqtt_discovery"):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", APP / f"{name}.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

DiscoveryPayloads = sys.modules[f"{PACKAGE}.mqtt_discovery"].DiscoveryPayloads
MinerSnapshot = sys.modules[f"{PACKAGE}.xmrig_monitor"].MinerSnapshot


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.builder = DiscoveryPayloads()

    def test_has_eight_entities(self):
        self.assertEqual(len(self.builder.discovery_messages()), 8)

    def test_unique_topics(self):
        topics = [m.topic for m in self.builder.discovery_messages()]
        self.assertEqual(len(topics), len(set(topics)))

    def test_discovery_retained(self):
        self.assertTrue(all(m.retain for m in self.builder.discovery_messages()))

    def test_no_credentials_in_discovery(self):
        text = "".join(m.payload for m in self.builder.discovery_messages())
        self.assertNotIn("wallet", text)
        self.assertNotIn("password", text)

    def test_home_assistant_schema(self):
        for msg in self.builder.discovery_messages():
            p = json.loads(msg.payload)
            self.assertIn("unique_id", p)
            self.assertIn("state_topic", p)
            self.assertIn("device", p)
            self.assertTrue(msg.topic.endswith("/config"))

    def test_reject_unsafe_topics(self):
        for kw in ({"node_id": "foo/#"}, {"prefix": "ha +"}, {"base_topic": "../bad"}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                DiscoveryPayloads(**kw)

    def test_snapshot_metrics(self):
        snap = MinerSnapshot(True, hashrate_10s=50.5, accepted=3, pool_connected=True)
        msgs = self.builder.telemetry_messages(snap, process_running=True)
        self.assertEqual([m.payload for m in msgs[:2]], ["online", "online"])
        data = json.loads(msgs[2].payload)
        self.assertEqual(data["hashrate_10s"], 50.5)
        self.assertEqual(data["accepted"], 3)
        self.assertEqual(data["pool_connected"], "true")
        self.assertIsNone(data["hashrate_60s"])

    def test_api_failure_does_not_publish_old_values(self):
        snap = MinerSnapshot(False, hashrate_10s=88.0)
        msgs = self.builder.telemetry_messages(snap, process_running=True)
        self.assertEqual([m.payload for m in msgs[:2]], ["online", "offline"])
        self.assertIsNone(json.loads(msgs[2].payload)["hashrate_10s"])

    def test_process_stopped(self):
        snap = MinerSnapshot(True, hashrate_10s=100.0)
        msgs = self.builder.telemetry_messages(snap, process_running=False)
        self.assertEqual([m.payload for m in msgs[:2]], ["offline", "offline"])
        self.assertIsNone(json.loads(msgs[2].payload)["hashrate_10s"])

    def test_unknown_pool_state(self):
        snap = MinerSnapshot(True, pool_connected=None)
        data = json.loads(self.builder.telemetry_messages(snap, process_running=True)[2].payload)
        self.assertIsNone(data["pool_connected"])

    def test_nan_not_sent(self):
        snap = MinerSnapshot(True, hashrate_10s=float("nan"))
        data = json.loads(self.builder.telemetry_messages(snap, process_running=True)[2].payload)
        self.assertIsNone(data["hashrate_10s"])

    def test_telemetry_not_retained(self):
        snap = MinerSnapshot(True)
        msgs = self.builder.telemetry_messages(snap, process_running=True)
        self.assertFalse(msgs[-1].retain)


if __name__ == "__main__":
    unittest.main()
