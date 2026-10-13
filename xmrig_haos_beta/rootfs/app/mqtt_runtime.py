"""Optional MQTT startup wiring for the HAOS Python candidate.

Only the Python entrypoint calls this adapter. Missing Supervisor MQTT service
must never prevent miner startup; no credentials are logged.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from .mqtt_client import MqttPublisher
from .mqtt_service import BrokerSettings, MqttConfigError, fetch_supervisor_mqtt

LOG = logging.getLogger("xmrig-mqtt")


def load_mqtt_publisher(
    *,
    service_loader: Callable[[], BrokerSettings] = fetch_supervisor_mqtt,
    publisher_factory: Callable[[BrokerSettings], MqttPublisher] = MqttPublisher,
) -> MqttPublisher | None:
    """Create optional publisher; returning None is a safe offline fallback."""
    try:
        settings = service_loader()
        return publisher_factory(settings)
    except (MqttConfigError, OSError, ValueError, ImportError):
        LOG.info("MQTT service unavailable; controller continues without MQTT")
        return None
