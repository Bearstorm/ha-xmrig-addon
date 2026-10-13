"""Pure Home Assistant MQTT Discovery payload builder for XMRig.

No broker connection, passwords, or process-control code lives here.
The publishing transport will be a separate opt-in adapter.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any

from .xmrig_monitor import MinerSnapshot


SENSORS = (
    ("hashrate_10s", "Hashrate 10s", "H/s", "measurement", "mdi:speedometer"),
    ("hashrate_60s", "Hashrate 60s", "H/s", "measurement", "mdi:speedometer"),
    ("hashrate_15m", "Hashrate 15m", "H/s", "measurement", "mdi:speedometer"),
    ("accepted", "Accepted shares", None, "total_increasing", "mdi:check-circle-outline"),
    ("rejected", "Rejected shares", None, "total_increasing", "mdi:close-circle-outline"),
    ("uptime_seconds", "Uptime", "s", "measurement", "mdi:timer-outline"),
)


@dataclass(frozen=True)
class MqttMessage:
    topic: str
    payload: str
    retain: bool = False
    qos: int = 0


class DiscoveryPayloads:
    """Create fixed-shape MQTT messages; never serialize wallet or pool credentials."""

    def __init__(self, *, node_id: str = "xmrig_haos", prefix: str = "homeassistant",
                 base_topic: str = "xmrig_haos") -> None:
        for name, value in (("node_id", node_id), ("prefix", prefix), ("base_topic", base_topic)):
            if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", value):
                raise ValueError(f"invalid {name}")
        if "/" in node_id:
            raise ValueError("node_id must not contain slashes")
        self.node_id = node_id
        self.prefix = prefix
        self.base_topic = base_topic

    @property
    def telemetry_topic(self) -> str:
        return f"{self.base_topic}/telemetry"

    @property
    def api_availability_topic(self) -> str:
        return f"{self.base_topic}/api_availability"

    @property
    def process_availability_topic(self) -> str:
        return f"{self.base_topic}/process_availability"

    def discovery_messages(self) -> list[MqttMessage]:
        device = {"identifiers": [self.node_id], "name": "XMRig Miner 2.0",
                  "manufacturer": "XMRig", "model": "HAOS Safe"}
        messages: list[MqttMessage] = []
        for key, label, unit, state_class, icon in SENSORS:
            payload: dict[str, Any] = {
                "name": label,
                "unique_id": f"{self.node_id}_{key}",
                "object_id": f"{self.node_id}_{key}",
                "state_topic": self.telemetry_topic,
                "value_template": "{{ value_json." + key + " }}",
                "availability_topic": self.api_availability_topic,
                "payload_available": "online",
                "payload_not_available": "offline",
                "icon": icon,
                "device": device,
            }
            if unit is not None:
                payload["unit_of_measurement"] = unit
            if state_class:
                payload["state_class"] = state_class
            messages.append(MqttMessage(
                f"{self.prefix}/sensor/{self.node_id}/{key}/config",
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                retain=True,
            ))
        for key, label, availability_topic in (
            ("api_available", "HTTP API available", self.process_availability_topic),
            ("pool_connected", "Pool connected", self.api_availability_topic),
        ):
            payload = {
                "name": label,
                "unique_id": f"{self.node_id}_{key}",
                "object_id": f"{self.node_id}_{key}",
                "state_topic": self.telemetry_topic,
                "value_template": "{{ value_json." + key + " }}",
                "payload_on": "true",
                "payload_off": "false",
                "availability_topic": availability_topic,
                "payload_available": "online",
                "payload_not_available": "offline",
                "device": device,
            }
            messages.append(MqttMessage(
                f"{self.prefix}/binary_sensor/{self.node_id}/{key}/config",
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                retain=True,
            ))
        return messages

    def telemetry_messages(self, snapshot: MinerSnapshot, *, process_running: bool) -> list[MqttMessage]:
        if not isinstance(snapshot, MinerSnapshot) or not isinstance(process_running, bool):
            raise ValueError("invalid telemetry input")
        # Do not emit stale metric values when the API is unavailable.
        available = bool(process_running and snapshot.api_available)
        data: dict[str, Any] = {}
        for key, *_ in SENSORS:
            val = getattr(snapshot, key) if available else None
            if isinstance(val, float) and not math.isfinite(val):
                val = None
            data[key] = val
        data["api_available"] = "true" if available else "false"
        data["pool_connected"] = (
            "true" if snapshot.pool_connected else "false"
        ) if available and snapshot.pool_connected is not None else None
        return [
            MqttMessage(self.process_availability_topic,
                        "online" if process_running else "offline", retain=True),
            MqttMessage(self.api_availability_topic,
                        "online" if available else "offline", retain=True),
            MqttMessage(self.telemetry_topic,
                        json.dumps(data, separators=(",", ":"), allow_nan=False), retain=False),
        ]
