"""MQTT publisher transport unit tests, no network or paho installation."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "xmrig_haos" / "rootfs" / "app"
PKG = "mqtt_publisher_test_pkg"
module = types.ModuleType(PKG)
module.__path__ = [str(ROOT)]
sys.modules[PKG] = module
for name in ("xmrig_monitor", "mqtt_discovery", "mqtt_service", "mqtt_commands", "mqtt_client"):
    spec = importlib.util.spec_from_file_location(f"{PKG}.{name}", ROOT / f"{name}.py")
    assert spec is not None and spec.loader is not None
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)

mod = sys.modules[f"{PKG}.mqtt_client"]
BrokerSettings = sys.modules[f"{PKG}.mqtt_service"].BrokerSettings
MinerSnapshot = sys.modules[f"{PKG}.xmrig_monitor"].MinerSnapshot


class FakePublishResult:
    def __init__(self, rc=0):
        self.rc = rc


class FakeClient:
    def __init__(self):
        self.records = []
        self.on_connect = None
        self.on_disconnect = None
        self.fail_publish = False
        self.fail_connect = False
        self.loop_started = False
        self.loop_stopped = False
        self.disconnect_calls = 0
        self.login = None
        self.tls = False
        self.will = None
        self.endpoint = None
        self.subscriptions = []
        self.on_message = None

    def username_pw_set(self, user, password):
        self.login = (user, password)

    def tls_set(self):
        self.tls = True

    def will_set(self, *args, **kwargs):
        self.will = (args, kwargs)

    def reconnect_delay_set(self, **kwargs):
        pass

    def connect_async(self, host, port, keepalive):
        if self.fail_connect:
            raise OSError("broker unavailable")
        self.endpoint = (host, port, keepalive)

    def loop_start(self):
        self.loop_started = True

    def loop_stop(self):
        self.loop_stopped = True

    def disconnect(self):
        self.disconnect_calls += 1

    def publish(self, topic, payload, qos=0, retain=False):
        self.records.append((topic, payload, qos, retain))
        return FakePublishResult(1 if self.fail_publish else 0)

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))
        return (0, 1)

    def incoming(self, payload, *, retain=False, topic="xmrig_haos/command"):
        msg = types.SimpleNamespace(topic=topic, payload=payload, retain=retain)
        self.on_message(self, None, msg)

    def connected(self, reason=0):
        self.on_connect(self, None, None, reason, None)

    def disconnected(self):
        self.on_disconnect(self, None, None, 1, None)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.pub = mod.MqttPublisher(
            BrokerSettings("core-mosquitto", 1883, "user", "secret"),
            client_factory=lambda: self.client,
        )

    def test_subscribes_command_topic(self):
        self.pub.start()
        self.client.connected()
        self.assertEqual(self.client.subscriptions, [("xmrig_haos/command", 1)])

    def test_strict_command_callback(self):
        self.pub.start()
        self.client.connected()
        self.client.incoming(b"OFF")
        self.assertEqual(self.pub.commands.take(), "OFF")
        self.client.incoming(b"ON", retain=True)
        self.assertIsNone(self.pub.commands.take())
        self.client.incoming(b"ON", topic="other/command")
        self.assertIsNone(self.pub.commands.take())

    def test_start_connect_async(self):
        self.assertTrue(self.pub.start())
        self.assertEqual(self.client.endpoint, ("core-mosquitto", 1883, 60))
        self.assertTrue(self.client.loop_started)

    def test_not_connected_until_callback(self):
        self.pub.start()
        self.assertFalse(self.pub.connected)
        self.assertFalse(self.pub.publish(MinerSnapshot(True), process_running=True))

    def test_discovery_sent_on_connect(self):
        self.pub.start()
        self.client.connected()
        self.assertTrue(self.pub.connected)
        self.assertEqual(len(self.client.records), 9)
        self.assertTrue(all(m[3] for m in self.client.records))

    def test_republish_discovery_on_reconnect(self):
        self.pub.start()
        self.client.connected()
        self.client.disconnected()
        self.assertFalse(self.pub.connected)
        self.client.connected()
        self.assertEqual(len(self.client.records), 18)

    def test_telemetry_messages(self):
        self.pub.start()
        self.client.connected()
        self.assertTrue(self.pub.publish(MinerSnapshot(True, hashrate_10s=99), process_running=True))
        self.assertEqual(len(self.client.records), 12)
        self.assertIn("99", self.client.records[-1][1])
        self.assertFalse(self.client.records[-1][3])

    def test_unavailable_mqtt_nonfatal(self):
        self.client.fail_connect = True
        self.assertFalse(self.pub.start())
        self.assertFalse(self.pub.connected)
        self.assertFalse(self.pub.publish(MinerSnapshot(True), process_running=True))

    def test_login_is_not_published(self):
        self.pub.start()
        self.client.connected()
        self.pub.publish(MinerSnapshot(True), process_running=True)
        self.assertNotIn("secret", repr(self.client.records))

    def test_tls_option(self):
        pub = mod.MqttPublisher(BrokerSettings("broker", 8883, tls=True), client_factory=lambda: self.client)
        self.assertTrue(pub.start())
        self.assertTrue(self.client.tls)

    def test_refused_connection(self):
        self.pub.start()
        self.client.connected(reason=5)
        self.assertFalse(self.pub.connected)

    def test_close_marks_offline(self):
        self.pub.start()
        self.client.connected()
        self.pub.close()
        self.assertEqual(self.client.records[-1][1], "offline")
        self.assertEqual(self.client.disconnect_calls, 1)
        self.assertTrue(self.client.loop_stopped)

    def test_close_idempotent(self):
        self.pub.start()
        self.client.connected()
        self.pub.close()
        self.pub.close()
        self.assertEqual(self.client.disconnect_calls, 1)

    def test_close_without_connection(self):
        self.pub.start()
        self.pub.close()
        self.assertEqual(self.client.disconnect_calls, 0)
        self.assertTrue(self.client.loop_stopped)

    def test_no_duplicate_start(self):
        self.assertTrue(self.pub.start())
        self.assertFalse(self.pub.start())

    def test_publish_failure_no_exception(self):
        self.pub.start()
        self.client.connected()
        self.client.fail_publish = True
        self.assertFalse(self.pub.publish(MinerSnapshot(True), process_running=True))

    def test_missing_library_nonfatal(self):
        pub = mod.MqttPublisher(BrokerSettings("broker", 1883),
                                client_factory=lambda: (_ for _ in ()).throw(ImportError("paho")))
        self.assertFalse(pub.start())

    def test_last_will_offline(self):
        self.pub.start()
        args, kwargs = self.client.will
        self.assertEqual(args[1], "offline")
        self.assertTrue(kwargs["retain"])

    def test_cannot_reopen_closed_client(self):
        self.pub.close()
        self.assertFalse(self.pub.start())


if __name__ == "__main__":
    unittest.main()
