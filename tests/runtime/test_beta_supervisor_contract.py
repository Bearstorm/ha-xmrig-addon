"""Supervisor MQTT service contract against a local fake HTTP server.

No real Supervisor token, broker, Home Assistant, or mining process used.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "xmrig_haos_beta" / "rootfs"))

from app import mqtt_service
from app.mqtt_commands import CommandMailbox
from app.mqtt_discovery import DiscoveryPayloads
from app.mqtt_runtime import load_mqtt_publisher


class ServiceHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append((self.path, self.headers.get("Authorization")))
        if self.path != "/services/mqtt":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Bearer CI_FAKE_TOKEN":
            self.send_error(401)
            return
        body = json.dumps({
            "result": "ok",
            "data": {
                "host": "core-mosquitto",
                "port": 1883,
                "username": "ci-client",
                "password": "ci-secret",
                "ssl": False,
            },
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class BetaIsolationTests(unittest.TestCase):
    def test_beta_discovery_and_command_topics_are_unique(self):
        beta = DiscoveryPayloads()
        self.assertEqual(beta.command_topic, "xmrig_haos_beta/command")
        self.assertEqual(beta.telemetry_topic, "xmrig_haos_beta/telemetry")
        messages = beta.discovery_messages()
        self.assertEqual(len(messages), 21)
        self.assertTrue(all("xmrig_haos_beta" in msg.topic for msg in messages))
        self.assertTrue(all("xmrig_haos/" not in msg.topic for msg in messages))

    def test_stable_commands_cannot_reach_beta_mailbox(self):
        inbox = CommandMailbox()
        self.assertFalse(inbox.submit("xmrig_haos/command", b"OFF"))
        self.assertTrue(inbox.submit("xmrig_haos_beta/command", b"OFF"))
        self.assertEqual(inbox.take(), "OFF")
        self.assertIsNone(inbox.take())


class SupervisorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ServiceHandler)
        cls.server.requests = []
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.server.requests.clear()
        self.url = f"http://127.0.0.1:{self.server.server_port}/services/mqtt"

    def test_token_and_service_contract(self):
        with patch.object(mqtt_service, "SUPERVISOR_MQTT_URL", self.url):
            broker = mqtt_service.fetch_supervisor_mqtt(token="CI_FAKE_TOKEN")
        self.assertEqual(broker.host, "core-mosquitto")
        self.assertEqual(broker.port, 1883)
        self.assertEqual(broker.username, "ci-client")
        self.assertEqual(broker.password, "ci-secret")
        self.assertEqual(self.server.requests, [
            ("/services/mqtt", "Bearer CI_FAKE_TOKEN")
        ])
        self.assertNotIn("ci-secret", repr(broker))

    def test_missing_token_never_contacts_server(self):
        with patch.object(mqtt_service, "SUPERVISOR_MQTT_URL", self.url):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(mqtt_service.MqttConfigError):
                    mqtt_service.fetch_supervisor_mqtt()
        self.assertEqual(self.server.requests, [])

    def test_rejected_token_returns_generic_error(self):
        with patch.object(mqtt_service, "SUPERVISOR_MQTT_URL", self.url):
            with self.assertRaises(mqtt_service.MqttConfigError) as ctx:
                mqtt_service.fetch_supervisor_mqtt(token="WRONG_TOKEN")
        self.assertNotIn("WRONG_TOKEN", str(ctx.exception))

    def test_optional_adapter_does_not_connect_or_mine(self):
        captured = []
        def factory(settings):
            captured.append(settings)
            return object()
        with patch.object(mqtt_service, "SUPERVISOR_MQTT_URL", self.url):
            result = load_mqtt_publisher(
                service_loader=lambda: mqtt_service.fetch_supervisor_mqtt(token="CI_FAKE_TOKEN"),
                publisher_factory=factory,
            )
        self.assertIsNotNone(result)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].host, "core-mosquitto")

    def test_optional_adapter_handles_unauthorized(self):
        with patch.object(mqtt_service, "SUPERVISOR_MQTT_URL", self.url):
            result = load_mqtt_publisher(
                service_loader=lambda: mqtt_service.fetch_supervisor_mqtt(token="WRONG_TOKEN")
            )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
