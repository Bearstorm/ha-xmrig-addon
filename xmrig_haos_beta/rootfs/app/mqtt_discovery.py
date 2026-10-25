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
from .resource_monitor import ResourceSnapshot


SENSORS = (
    ("hashrate_10s", "Hashrate 10s", "H/s", "measurement", "mdi:speedometer"),
    ("hashrate_60s", "Hashrate 60s", "H/s", "measurement", "mdi:speedometer"),
    ("hashrate_15m", "Hashrate 15m", "H/s", "measurement", "mdi:speedometer"),
    ("accepted", "Accepted shares", None, "total_increasing", "mdi:check-circle-outline"),
    ("rejected", "Rejected shares", None, "total_increasing", "mdi:close-circle-outline"),
    ("uptime_seconds", "Uptime", "s", "measurement", "mdi:timer-outline"),
)

# Resource observations are independent of the XMRig HTTP API.
# Container values remain available when mining is OFF.
RESOURCE_SENSORS = (
    ("process_cpu_percent", "XMRig CPU usage", "%", "measurement", "mdi:cpu-64-bit", "process"),
    ("process_ram_mib", "XMRig RAM usage", "MiB", "measurement", "mdi:memory", "process"),
    ("process_ram_peak_mib", "XMRig RAM peak", "MiB", "measurement", "mdi:memory", "process"),
    ("process_threads", "XMRig OS threads", None, "measurement", "mdi:cpu-64-bit", "process"),
    ("process_cpu_seconds", "XMRig CPU time", "s", "total_increasing", "mdi:timer-outline", "process"),
    ("container_cpu_percent", "Add-on CPU usage", "%", "measurement", "mdi:cpu-64-bit", "container"),
    ("container_ram_mib", "Add-on RAM usage", "MiB", "measurement", "mdi:memory", "container"),
    ("container_net_rx_mib", "Add-on network received", "MiB", "total_increasing", "mdi:download-network", "container"),
    ("container_net_tx_mib", "Add-on network sent", "MiB", "total_increasing", "mdi:upload-network", "container"),
    ("container_disk_read_mib", "Add-on disk read", "MiB", "total_increasing", "mdi:harddisk", "container"),
    ("container_disk_write_mib", "Add-on disk written", "MiB", "total_increasing", "mdi:harddisk", "container"),
)


@dataclass(frozen=True)
class MqttMessage:
    topic: str
    payload: str
    retain: bool = False
    qos: int = 0


class DiscoveryPayloads:
    """Create fixed-shape MQTT messages; never serialize wallet or pool credentials."""

    def __init__(self, *, node_id: str = "xmrig_haos_thermal_test", prefix: str = "homeassistant",
                 base_topic: str = "xmrig_haos_thermal_test") -> None:
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
    def resources_topic(self) -> str:
        return f"{self.base_topic}/resources"

    @property
    def api_availability_topic(self) -> str:
        return f"{self.base_topic}/api_availability"

    @property
    def process_availability_topic(self) -> str:
        return f"{self.base_topic}/process_availability"

    @property
    def mqtt_availability_topic(self) -> str:
        return f"{self.base_topic}/mqtt_availability"

    @property
    def command_topic(self) -> str:
        return f"{self.base_topic}/command"

    def discovery_messages(self) -> list[MqttMessage]:
        device = {"identifiers": [self.node_id], "name": "XMRig Miner 2.0 Thermal Test",
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
        for key, label, unit, state_class, icon, scope in RESOURCE_SENSORS:
            payload = {
                "name": label,
                "unique_id": f"{self.node_id}_{key}",
                "object_id": f"{self.node_id}_{key}",
                "state_topic": self.resources_topic,
                "value_template": "{{ value_json." + key + " }}",
                "availability_topic": (self.process_availability_topic if scope == "process"
                                       else self.mqtt_availability_topic),
                "payload_available": "online",
                "payload_not_available": "offline",
                "icon": icon,
                "state_class": state_class,
                "device": device,
            }
            if unit is not None:
                payload["unit_of_measurement"] = unit
            if unit == "MiB":
                payload["device_class"] = "data_size"
            messages.append(MqttMessage(
                f"{self.prefix}/sensor/{self.node_id}/{key}/config",
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                retain=True,
            ))
        switch_config = {
            "name": "Mining",
            "unique_id": f"{self.node_id}_mining",
            "object_id": f"{self.node_id}_mining",
            "command_topic": self.command_topic,
            "state_topic": self.process_availability_topic,
            "availability_topic": self.mqtt_availability_topic,
            "payload_available": "online",
            "payload_not_available": "offline",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "online",
            "state_off": "offline",
            "optimistic": False,
            "retain": False,
            "icon": "mdi:pickaxe",
            "device": device,
        }
        messages.append(MqttMessage(
            f"{self.prefix}/switch/{self.node_id}/mining/config",
            json.dumps(switch_config, separators=(",", ":"), sort_keys=True),
            retain=True,
        ))
        return messages

    def obsolete_discovery_messages(self) -> list[MqttMessage]:
        """Clear only the retired beta RAM-percent Discovery configuration.

        MQTT retained empty payload deletes this precise configuration topic.
        No other entity, device, or stable addon is affected.
        """
        return [MqttMessage(
            f"{self.prefix}/sensor/{self.node_id}/container_ram_percent/config",
            "", retain=True, qos=1,
        )]

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

    def resource_messages(self, snapshot: ResourceSnapshot) -> list[MqttMessage]:
        """Publish numeric resource fields; unknown metrics are JSON null, not zero."""
        if not isinstance(snapshot, ResourceSnapshot):
            raise ValueError("invalid resource telemetry")
        data: dict[str, Any] = {}
        for key, *_ in RESOURCE_SENSORS:
            value = getattr(snapshot, key)
            if isinstance(value, float) and not math.isfinite(value):
                value = None
            data[key] = value
        return [MqttMessage(
            self.resources_topic,
            json.dumps(data, separators=(",", ":"), allow_nan=False),
            retain=False,
        )]
