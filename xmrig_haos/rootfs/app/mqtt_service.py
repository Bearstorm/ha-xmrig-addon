"""Discover optional MQTT broker credentials from Home Assistant Supervisor.

This module only resolves connection settings. It never connects to a broker,
publishes messages, controls mining or logs tokens/passwords.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping


SUPERVISOR_MQTT_URL = "http://supervisor/services/mqtt"
MAX_REPLY_BYTES = 16384


class MqttConfigError(ValueError):
    """An error safe to report without leaking broker credentials."""


@dataclass(frozen=True)
class BrokerSettings:
    host: str
    port: int
    username: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)
    tls: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host or len(self.host) > 255:
            raise MqttConfigError("Invalid MQTT host")
        if any(ord(c) <= 32 or ord(c) >= 127 for c in self.host):
            raise MqttConfigError("Invalid MQTT host")
        if any(c in self.host for c in "/\\@?#"):
            raise MqttConfigError("Invalid MQTT host")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise MqttConfigError("Invalid MQTT port")
        if not isinstance(self.tls, bool):
            raise MqttConfigError("Invalid MQTT TLS setting")
        for value in (self.username, self.password):
            if value is not None and (not isinstance(value, str) or len(value) > 1024 or any(ord(c) < 32 for c in value)):
                raise MqttConfigError("Invalid MQTT credentials")


def _port(value: Any) -> int:
    if isinstance(value, bool):
        raise MqttConfigError("Invalid MQTT port")
    if isinstance(value, int):
        port = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,5}", value):
        port = int(value)
    else:
        raise MqttConfigError("Invalid MQTT port")
    if not 1 <= port <= 65535:
        raise MqttConfigError("Invalid MQTT port")
    return port


def parse_supervisor_service(response: Any) -> BrokerSettings:
    """Parse the Supervisor JSON envelope or service mapping."""
    if not isinstance(response, Mapping):
        raise MqttConfigError("Invalid MQTT service response")
    if "result" in response:
        if response["result"] != "ok":
            raise MqttConfigError("MQTT service unavailable")
        response = response.get("data")
    if not isinstance(response, Mapping):
        raise MqttConfigError("MQTT service unavailable")
    ssl = response.get("ssl", False)
    if not isinstance(ssl, bool):
        raise MqttConfigError("Invalid MQTT TLS setting")
    return BrokerSettings(
        host=response.get("host"),
        port=_port(response.get("port")),
        username=response.get("username"),
        password=response.get("password"),
        tls=ssl,
    )


def manual_broker(options: Mapping[str, Any]) -> BrokerSettings:
    """Resolve manual MQTT settings without changing existing miner options."""
    if not isinstance(options, Mapping):
        raise MqttConfigError("Invalid manual MQTT settings")
    return BrokerSettings(
        host=options.get("mqtt_host"),
        port=_port(options.get("mqtt_port", 1883)),
        username=options.get("mqtt_username") or None,
        password=options.get("mqtt_password") or None,
        tls=options.get("mqtt_tls", False),
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_supervisor_mqtt(*, token: str | None = None, timeout: float = 2.0) -> BrokerSettings:
    """Read declared Supervisor MQTT service; no fallback to guessed credentials."""
    if token is None:
        token = os.environ.get("SUPERVISOR_TOKEN")
    if not isinstance(token, str) or not token or any(c in token for c in "\r\n"):
        raise MqttConfigError("Supervisor authentication unavailable")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 10:
        raise MqttConfigError("Invalid Supervisor timeout")
    request = urllib.request.Request(
        SUPERVISOR_MQTT_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status != 200:
                raise MqttConfigError("MQTT service unavailable")
            body = response.read(MAX_REPLY_BYTES + 1)
        if len(body) > MAX_REPLY_BYTES:
            raise MqttConfigError("MQTT service response too large")
        return parse_supervisor_service(json.loads(body.decode("utf-8")))
    except (urllib.error.URLError, OSError, TimeoutError, ValueError, UnicodeError) as exc:
        if isinstance(exc, MqttConfigError):
            raise
        raise MqttConfigError("Unable to read Supervisor MQTT service") from None
