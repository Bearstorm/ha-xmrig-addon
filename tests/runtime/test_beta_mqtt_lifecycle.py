"""Beta MQTT lifecycle race tests. No network, MQTT broker, or mining process."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "xmrig_haos_beta" / "rootfs"))

from app.mqtt_client import MqttPublisher
from app.mqtt_service import BrokerSettings
from app.xmrig_monitor import MinerSnapshot


class FakeClient:
    def __init__(self):
        self.records = []
        self.subscribed = []
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None

    def connect_async(self, *args, **kwargs):
        return None

    def loop_start(self):
        return None

    def loop_stop(self):
        return None

    def reconnect_delay_set(self, **kwargs):
        return None

    def will_set(self, *args, **kwargs):
        return None

    def publish(self, topic, payload, *, qos=0, retain=False):
        self.records.append((topic, payload, retain))
        return SimpleNamespace(rc=0)

    def subscribe(self, topic, qos=0):
        self.subscribed.append(topic)
        return (0, 1)

    def disconnect(self):
        return None

    def incoming(self, text, *, retained=False, topic="xmrig_haos_beta/command"):
        self.on_message(self, None, SimpleNamespace(
            topic=topic, payload=text, retain=retained,
        ))

    def connected(self, code=0):
        self.on_connect(self, None, None, code)

    def disconnected(self):
        self.on_disconnect(self, None, None, 1)


class BetaMqttLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.pub = MqttPublisher(BrokerSettings("broker.invalid", 1883),
                                 client_factory=lambda: self.client)
        self.assertTrue(self.pub.start())

    def tearDown(self):
        self.pub.close()

    def test_message_before_connection_rejected(self):
        self.client.incoming(b"ON")
        self.assertIsNone(self.pub.commands.take())

    def test_pending_command_discarded_on_disconnect(self):
        self.client.connected()
        self.client.incoming(b"ON")
        self.client.disconnected()
        self.assertIsNone(self.pub.commands.take())

    def test_late_offline_message_rejected(self):
        self.client.connected()
        self.client.disconnected()
        self.client.incoming(b"ON")
        self.assertIsNone(self.pub.commands.take())

    def test_reconnect_rejects_retained_but_accepts_fresh(self):
        self.client.connected()
        self.client.disconnected()
        self.client.incoming(b"ON")
        self.client.connected()
        self.client.incoming(b"ON", retained=True)
        self.assertIsNone(self.pub.commands.take())
        self.client.incoming(b"OFF")
        self.assertEqual(self.pub.commands.take(), "OFF")

    def test_burst_latest_state_wins(self):
        self.client.connected()
        self.client.incoming(b"ON")
        self.client.incoming(b"OFF")
        self.client.incoming(b"ON")
        self.client.incoming(b"OFF")
        self.assertEqual(self.pub.commands.take(), "OFF")
        self.assertIsNone(self.pub.commands.take())

    def test_commands_from_unrelated_topic_ignored(self):
        self.client.connected()
        self.client.incoming(b"ON", topic="xmrig_haos/command")
        self.assertIsNone(self.pub.commands.take())

    def test_stale_client_callbacks_do_not_change_live_state(self):
        self.client.connected()
        stale = FakeClient()
        self.pub._on_disconnect(stale, None, None, 1)
        self.assertTrue(self.pub.connected)
        self.pub._on_connect(stale, None, None, 5)
        self.assertTrue(self.pub.connected)
        self.pub._on_message(stale, None, SimpleNamespace(
            topic="xmrig_haos_beta/command", payload=b"ON", retain=False,
        ))
        self.assertIsNone(self.pub.commands.take())

    def test_reconnect_republishes_process_not_commands(self):
        self.client.connected()
        self.pub.publish(MinerSnapshot(False), process_running=False)
        self.client.incoming(b"ON")
        self.client.disconnected()
        self.assertIsNone(self.pub.commands.take())
        old_count = len(self.client.records)
        self.client.connected()
        delta = self.client.records[old_count:]
        self.assertTrue(any(topic == "xmrig_haos_beta/process_availability"
                            and payload == "offline" for topic, payload, _ in delta))
        self.assertTrue(any(topic == "xmrig_haos_beta/mqtt_availability"
                            and payload == "online" for topic, payload, _ in delta))
        self.assertIsNone(self.pub.commands.take())


if __name__ == "__main__":
    unittest.main(verbosity=2)
