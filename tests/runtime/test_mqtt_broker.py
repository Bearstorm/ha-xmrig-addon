"""Local Mosquitto integration tests; only run on a CI runner test broker.

Never starts XMRig, contacts a real mining pool, or uses Home Assistant tokens.
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import unittest
from pathlib import Path

import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "xmrig_haos" / "rootfs"))
from app.mqtt_client import MqttPublisher
from app.mqtt_discovery import DiscoveryPayloads
from app.mqtt_service import BrokerSettings
from app.xmrig_monitor import MinerSnapshot

HOST = "127.0.0.1"
PORT = int(os.environ.get("XMRIG_TEST_MQTT_PORT", "18883"))


class LocalBrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.messages: queue.Queue[tuple[str, str, bool]] = queue.Queue()
        self.observer_connected = threading.Event()
        self.observer = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="xmrig-test-observer",
            protocol=mqtt.MQTTv311,
        )

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                client.subscribe("homeassistant/+/xmrig_haos/+/config", qos=1)
                client.subscribe("xmrig_haos/#", qos=1)
                self.observer_connected.set()

        def on_message(client, userdata, message):
            self.messages.put((message.topic, message.payload.decode("utf-8"), message.retain))

        self.observer.on_connect = on_connect
        self.observer.on_message = on_message
        self.observer.connect(HOST, PORT, keepalive=20)
        self.observer.loop_start()
        self.assertTrue(self.observer_connected.wait(6), "local MQTT observer did not connect")
        self.publisher = MqttPublisher(BrokerSettings(HOST, PORT), discovery=DiscoveryPayloads())
        self.assertTrue(self.publisher.start())
        self.assertTrue(self._wait_until(lambda: self.publisher.connected, 6),
                        "XMRig MQTT publisher did not connect")

    def tearDown(self) -> None:
        self.publisher.close()
        self.observer.disconnect()
        self.observer.loop_stop()

    @staticmethod
    def _wait_until(predicate, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return predicate()

    def _collect(self, predicate, count, timeout=6):
        found = []
        deadline = time.monotonic() + timeout
        while len(found) < count and time.monotonic() < deadline:
            try:
                msg = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if predicate(msg):
                found.append(msg)
        self.assertEqual(len(found), count, f"only {len(found)} of {count} matching MQTT messages")
        return found

    def test_discovery_retained_in_real_broker(self):
        # New subscribers must receive retained Home Assistant Discovery config.
        observer2 = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                client_id="xmrig-test-retained-reader")
        items = queue.Queue()
        ready = threading.Event()

        def connected(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                client.subscribe("homeassistant/+/xmrig_haos/+/config", qos=1)
                ready.set()

        observer2.on_connect = connected
        observer2.on_message = lambda c, u, m: items.put((m.topic, m.payload, m.retain))
        try:
            observer2.connect(HOST, PORT, 20)
            observer2.loop_start()
            self.assertTrue(ready.wait(5))
            discovery = []
            until = time.monotonic() + 6
            while len(discovery) < 8 and time.monotonic() < until:
                try:
                    discovery.append(items.get(timeout=max(0.01, until - time.monotonic())))
                except queue.Empty:
                    break
            self.assertEqual(len(discovery), 8)
            self.assertTrue(all(item[2] for item in discovery))
            self.assertEqual(len({item[0] for item in discovery}), 8)
            for topic, payload, retained in discovery:
                self.assertIn("unique_id", json.loads(payload))
                self.assertNotIn(b"wallet", payload)
        finally:
            observer2.disconnect()
            observer2.loop_stop()

    def test_telemetry_and_availability_reach_real_broker(self):
        snapshot = MinerSnapshot(True, hashrate_10s=123.5, accepted=7, pool_connected=True)
        # Retained availability from earlier tests must not count as new output.
        time.sleep(0.15)
        while not self.messages.empty():
            self.messages.get_nowait()
        self.assertTrue(self.publisher.publish(snapshot, process_running=True))
        msgs = self._collect(lambda m: m[0] in {
            "xmrig_haos/telemetry", "xmrig_haos/api_availability",
            "xmrig_haos/process_availability"
        }, 3)
        by_topic = {topic: payload for topic, payload, retained in msgs}
        self.assertEqual(by_topic["xmrig_haos/api_availability"], "online")
        self.assertEqual(by_topic["xmrig_haos/process_availability"], "online")
        data = json.loads(by_topic["xmrig_haos/telemetry"])
        self.assertEqual(data["hashrate_10s"], 123.5)
        self.assertEqual(data["accepted"], 7)
        self.assertEqual(data["pool_connected"], "true")

    def test_api_failure_clears_old_values(self):
        self.assertTrue(self.publisher.publish(
            MinerSnapshot(False, hashrate_10s=999), process_running=True
        ))
        msgs = self._collect(lambda m: m[0] == "xmrig_haos/telemetry", 1)
        self.assertIsNone(json.loads(msgs[0][1])["hashrate_10s"])
        self.assertEqual(json.loads(msgs[0][1])["api_available"], "false")


if __name__ == "__main__":
    unittest.main(verbosity=2)
