"""Offline tests for Supervisor MQTT configuration and manual fallback."""
import importlib.util
import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "xmrig_haos" / "rootfs" / "app"
PACKAGE = "mqtt_service_test_pkg"
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(APP)]
sys.modules[PACKAGE] = pkg
spec = importlib.util.spec_from_file_location(f"{PACKAGE}.mqtt_service", APP / "mqtt_service.py")
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class DummyResponse:
    status = 200

    def __init__(self, body):
        self.body = io.BytesIO(body)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.body.close()

    def read(self, n):
        return self.body.read(n)


class DummyOpener:
    def __init__(self, body):
        self.body = body
        self.request = None

    def open(self, request, timeout):
        self.request = request
        return DummyResponse(self.body)


class BrokerTests(unittest.TestCase):
    def test_supervisor_envelope(self):
        service = mod.parse_supervisor_service({"result": "ok", "data": {
            "host": "core-mosquitto", "port": "1883", "username": "u", "password": "secret", "ssl": False
        }})
        self.assertEqual((service.host, service.port), ("core-mosquitto", 1883))
        self.assertEqual(service.password, "secret")

    def test_credentials_hidden_in_repr(self):
        service = mod.BrokerSettings("broker", 1883, "usersecret", "passsecret")
        self.assertNotIn("usersecret", repr(service))
        self.assertNotIn("passsecret", repr(service))

    def test_direct_mapping(self):
        self.assertTrue(mod.parse_supervisor_service({"host": "broker", "port": 8883, "ssl": True}).tls)

    def test_service_failure(self):
        with self.assertRaises(mod.MqttConfigError):
            mod.parse_supervisor_service({"result": "error", "data": {"host": "broker", "port": 1883}})

    def test_no_service_data(self):
        with self.assertRaises(mod.MqttConfigError):
            mod.parse_supervisor_service({"result": "ok"})

    def test_reject_bad_ports(self):
        for port in (False, 0, 65536, "bad", "-1", "123456"):
            with self.subTest(port=port), self.assertRaises(mod.MqttConfigError):
                mod.parse_supervisor_service({"host": "broker", "port": port})

    def test_reject_bad_host(self):
        with self.assertRaises(mod.MqttConfigError):
            mod.BrokerSettings("broker/unsafe", 1883)

    def test_manual_fallback(self):
        value = mod.manual_broker({"mqtt_host": "private-broker", "mqtt_port": 1884, "mqtt_tls": True})
        self.assertEqual((value.host, value.port, value.tls), ("private-broker", 1884, True))

    def test_manual_no_host_rejected(self):
        with self.assertRaises(mod.MqttConfigError):
            mod.manual_broker({})

    def test_no_supervisor_token(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(mod.MqttConfigError):
            mod.fetch_supervisor_mqtt()

    def test_supervisor_request(self):
        opener = DummyOpener(b'{"result":"ok","data":{"host":"broker","port":"1883"}}')
        with patch.object(mod.urllib.request, "build_opener", return_value=opener):
            settings = mod.fetch_supervisor_mqtt(token="private_token")
        self.assertEqual(settings.host, "broker")
        self.assertEqual(opener.request.get_header("Authorization"), "Bearer private_token")
        self.assertEqual(opener.request.full_url, mod.SUPERVISOR_MQTT_URL)

    def test_malformed_json_secret_not_exposed(self):
        opener = DummyOpener(b'{"password":"super_secret",invalid}')
        with patch.object(mod.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(mod.MqttConfigError) as caught:
                mod.fetch_supervisor_mqtt(token="token_secret")
        self.assertNotIn("super_secret", str(caught.exception))
        self.assertNotIn("token_secret", str(caught.exception))

    def test_large_response_rejected(self):
        opener = DummyOpener(b"x" * (mod.MAX_REPLY_BYTES + 1))
        with patch.object(mod.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(mod.MqttConfigError):
                mod.fetch_supervisor_mqtt(token="valid")

    def test_redirect_disabled(self):
        self.assertIsNone(mod._NoRedirect().redirect_request(None, None, 302, "", {}, "https://other/"))

    def test_reject_invalid_ssl_type(self):
        with self.assertRaises(mod.MqttConfigError):
            mod.parse_supervisor_service({"host": "broker", "port": 1883, "ssl": "false"})


if __name__ == "__main__":
    unittest.main()
