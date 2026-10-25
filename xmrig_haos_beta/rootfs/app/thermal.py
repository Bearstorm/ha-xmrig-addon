"""Fail-closed optional thermal monitor via Supervisor Home Assistant API."""
import json
import math
import os
import re
import time
from datetime import datetime
from urllib.request import Request, urlopen

BASE = "http://supervisor/core/api"

class ThermalGuard:
    def __init__(self, path="/data/options.json"):
        with open(path, encoding="utf-8") as stream:
            options = json.load(stream)
        self.start_mode = options.get("mining_start_mode", "manual")
        if self.start_mode not in ("manual", "automatic") or not isinstance(self.start_mode, str):
            raise ValueError("Invalid mining start mode")
        self.enabled = options.get("thermal_protection_enabled", False)
        self.entity = options.get("thermal_sensor_entity", "")
        self.limit = options.get("thermal_limit", 80)
        self.timeout = options.get("thermal_sensor_timeout", 180)
        self.notifications = options.get("thermal_notifications", True)
        if not isinstance(self.enabled, bool) or not isinstance(self.notifications, bool):
            raise ValueError("Invalid thermal boolean option")
        if type(self.limit) is not int or not 40 <= self.limit <= 105:
            raise ValueError("Invalid temperature limit")
        if type(self.timeout) is not int or not 60 <= self.timeout <= 3600:
            raise ValueError("Invalid sensor timeout")
        if self.enabled and not re.fullmatch(r"sensor\.[a-z0-9_]+", self.entity):
            raise ValueError("Invalid temperature sensor entity")
        self.token = os.environ.get("SUPERVISOR_TOKEN", "")

    def api(self, endpoint, payload=None):
        if not self.token:
            raise ValueError("Supervisor token unavailable")
        body = None if payload is None else json.dumps(payload).encode()
        req = Request(BASE + endpoint, data=body,
            headers={"Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json"},
            method="POST" if body is not None else "GET")
        with urlopen(req, timeout=3) as response:
            return json.loads(response.read(32768))

    def check(self):
        if not self.enabled:
            return True, "disabled", None
        try:
            from urllib.parse import quote
            item = self.api("/states/" + quote(self.entity, safe=""))
            value = float(item["state"])
            if not math.isfinite(value):
                return False, "invalid_temperature", None
            if item.get("attributes", {}).get("unit_of_measurement") not in ("°C", "C"):
                return False, "invalid_temperature_unit", value
            reported = item.get("last_reported")
            if not isinstance(reported, str):
                return False, "missing_last_reported", value
            stamp = datetime.fromisoformat(reported.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return False, "invalid_timestamp", value
            age = time.time() - stamp.timestamp()
            if age < -30 or age > self.timeout:
                return False, "stale_sensor", value
            if value > self.limit:
                return False, "temperature_limit_exceeded", value
            return True, "ok", value
        except (OSError, ValueError, KeyError, TypeError, OverflowError, IndexError):
            return False, "sensor_unavailable", None

    def notify(self, reason, temperature):
        if not self.notifications:
            return
        value = "unavailable" if temperature is None else str(temperature) + " °C"
        try:
            self.api("/services/persistent_notification/create", {
                "title": "XMRig - Thermal Protection",
                "notification_id": "xmrig_haos_thermal_test_thermal",
                "message": "Mining shutdown requested. Reason: " + reason
                    + ". CPU temperature: " + value
                    + ". Configured limit: " + str(self.limit) + " °C."
            })
        except (OSError, ValueError, TypeError):
            pass
