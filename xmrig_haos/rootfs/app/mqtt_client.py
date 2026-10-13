"""Optional MQTT publishing transport, isolated from mining process lifecycle.

Requires paho-mqtt >= 2 only when a real connection is started.
A missing MQTT broker is never a reason to stop the miner.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from .mqtt_discovery import DiscoveryPayloads, MqttMessage
from .mqtt_service import BrokerSettings
from .xmrig_monitor import MinerSnapshot

LOG = logging.getLogger("xmrig-mqtt")


class MqttPublisher:
    """Best-effort telemetry publisher; reconnects handled by the MQTT client."""

    def __init__(
        self,
        settings: BrokerSettings,
        *,
        discovery: DiscoveryPayloads | None = None,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._discovery = discovery if discovery is not None else DiscoveryPayloads()
        self._factory = client_factory
        self._client: Any = None
        self._lock = threading.RLock()
        self._started = False
        self._connected = False
        self._closed = False

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._connected and not self._closed

    def _new_client(self) -> Any:
        if self._factory is not None:
            return self._factory()
        # Lazy import keeps existing HAOS add-on operational without paho.
        import paho.mqtt.client as mqtt
        return mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="xmrig-haos-monitor",
            protocol=mqtt.MQTTv311,
        )

    @staticmethod
    def _publish(client: Any, msg: MqttMessage) -> bool:
        result = client.publish(msg.topic, msg.payload, qos=msg.qos, retain=msg.retain)
        # Paho MQTT_ERR_SUCCESS == 0; mock clients may expose .rc as well.
        rc = result[0] if isinstance(result, tuple) else getattr(result, "rc", None)
        return rc == 0

    def _on_connect(self, client: Any, userdata: Any, flags: Any,
                    reason_code: Any, properties: Any = None) -> None:
        # paho v2 reason codes compare to zero on successful connection.
        if reason_code != 0:
            with self._lock:
                self._connected = False
            LOG.warning("MQTT connection refused")
            return
        with self._lock:
            if self._closed or client is not self._client:
                return
            self._connected = True
            try:
                for msg in self._discovery.discovery_messages():
                    if not self._publish(client, msg):
                        LOG.warning("MQTT Discovery publish was not accepted")
                        break
            except (OSError, RuntimeError, ValueError):
                LOG.warning("MQTT Discovery publishing failed")

    def _on_disconnect(self, client: Any, userdata: Any, flags: Any,
                       reason_code: Any, properties: Any = None) -> None:
        with self._lock:
            self._connected = False

    def start(self) -> bool:
        """Start MQTT network thread once; never raise broker errors to miner."""
        with self._lock:
            if self._closed or self._started:
                return False
            client = None
            try:
                client = self._new_client()
                client.on_connect = self._on_connect
                client.on_disconnect = self._on_disconnect
                if self._settings.username is not None:
                    client.username_pw_set(self._settings.username, self._settings.password)
                if self._settings.tls:
                    client.tls_set()
                client.will_set(self._discovery.process_availability_topic, "offline", qos=1, retain=True)
                client.reconnect_delay_set(min_delay=2, max_delay=60)
                self._client = client
                self._started = True
                client.connect_async(self._settings.host, self._settings.port, keepalive=60)
                client.loop_start()
                return True
            except (ImportError, OSError, RuntimeError, ValueError, AttributeError):
                LOG.warning("Optional MQTT connection could not start")
                self._started = False
                self._connected = False
                self._client = None
                if client is not None:
                    try:
                        client.loop_stop()
                    except (OSError, RuntimeError, AttributeError):
                        pass
                return False

    def publish(self, snapshot: MinerSnapshot, *, process_running: bool) -> bool:
        """Best effort. Never holds or logs mining credentials."""
        with self._lock:
            if not self._connected or self._closed or self._client is None:
                return False
            try:
                messages = self._discovery.telemetry_messages(
                    snapshot, process_running=process_running
                )
                return all(self._publish(self._client, message) for message in messages)
            except (OSError, RuntimeError, ValueError):
                LOG.warning("MQTT telemetry publishing failed")
                return False

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            client = self._client
            connected = self._connected
            self._connected = False
            self._client = None
        if client is None:
            return
        try:
            if connected:
                self._publish(client, MqttMessage(
                    self._discovery.process_availability_topic, "offline", retain=True, qos=1
                ))
                client.disconnect()
        except (OSError, RuntimeError, ValueError):
            LOG.warning("MQTT clean disconnect failed")
        finally:
            try:
                client.loop_stop()
            except (OSError, RuntimeError, AttributeError):
                LOG.warning("MQTT loop shutdown failed")
