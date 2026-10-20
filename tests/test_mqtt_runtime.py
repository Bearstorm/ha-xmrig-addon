"""Tests for optional MQTT bootstrap; no Supervisor or broker required."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "xmrig_haos" / "rootfs" / "app"
PKG = "mqtt_runtime_test_package"
package = types.ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package
for name in ("xmrig_monitor", "mqtt_discovery", "mqtt_service", "mqtt_client", "mqtt_runtime"):
    spec = importlib.util.spec_from_file_location(f"{PKG}.{name}", ROOT / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
runtime = sys.modules[f"{PKG}.mqtt_runtime"]
service = sys.modules[f"{PKG}.mqtt_service"]


class RuntimeBootstrapTests(unittest.TestCase):
    def test_resolves_supervisor_config_without_mining(self):
        broker = service.BrokerSettings("core-mosquitto", 1883)
        marker = object()
        result = runtime.load_mqtt_publisher(
            service_loader=lambda: broker,
            publisher_factory=lambda settings: marker if settings is broker else None,
        )
        self.assertIs(result, marker)

    def test_no_service_returns_none(self):
        def absent():
            raise service.MqttConfigError("no service")
        self.assertIsNone(runtime.load_mqtt_publisher(service_loader=absent))

    def test_network_error_returns_none(self):
        def timeout():
            raise OSError("secret")
        self.assertIsNone(runtime.load_mqtt_publisher(service_loader=timeout))

    def test_bad_publisher_config_returns_none(self):
        broker = service.BrokerSettings("broker", 1883)
        def invalid(settings):
            raise ValueError("invalid")
        self.assertIsNone(runtime.load_mqtt_publisher(
            service_loader=lambda: broker, publisher_factory=invalid
        ))


if __name__ == "__main__":
    unittest.main()
