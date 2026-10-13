"""Read-only XMRig telemetry from its container-local HTTP API.

This module never starts/stops XMRig and has no MQTT dependencies.
The XMRig process must separately enable a restricted API bound to 127.0.0.1.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_API_PORT = 18080
DEFAULT_TIMEOUT_SECONDS = 2.0
MAX_RESPONSE_BYTES = 256 * 1024


@dataclass(frozen=True)
class MinerSnapshot:
    """Single poll; None indicates unavailable telemetry, never an assumed zero."""

    api_available: bool
    hashrate_10s: float | None = None
    hashrate_60s: float | None = None
    hashrate_15m: float | None = None
    accepted: int | None = None
    rejected: int | None = None
    uptime_seconds: int | None = None
    pool_connected: bool | None = None
    error: str | None = None


def _nonnegative_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _object(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _hashrate(value: Any, index: int) -> float | None:
    if not isinstance(value, list) or len(value) <= index:
        return None
    return _nonnegative_number(value[index])


def parse_summary(payload: Any) -> MinerSnapshot:
    """Parse XMRig /2/summary; ignore missing and unexpected fields safely."""
    if not isinstance(payload, dict):
        return MinerSnapshot(api_available=False, error="invalid_payload")

    hashrate = _object(payload.get("hashrate"))
    results = _object(payload.get("results"))
    connection = _object(payload.get("connection"))

    # XMRig publishes three windows in hashrate.total: 10s, 60s, 15m.
    totals = hashrate.get("total")

    accepted = _nonnegative_int(connection.get("accepted"))
    rejected = _nonnegative_int(connection.get("rejected"))
    if accepted is None:
        accepted = _nonnegative_int(results.get("shares_good"))
    if rejected is None:
        good = _nonnegative_int(results.get("shares_good"))
        total = _nonnegative_int(results.get("shares_total"))
        if good is not None and total is not None and total >= good:
            rejected = total - good

    pool_connected: bool | None = None
    # XMRig 6.26.0 does not normally emit a `connected` field. Its
    # connection.uptime_ms is calculated from the currently active connection
    # and becomes zero when no connection is active. A zero is ambiguous at
    # the instant of connection, so it is not interpreted as False.
    # Older API responses may only expose connection.uptime (whole seconds).
    if isinstance(connection.get("connected"), bool):
        pool_connected = connection["connected"]
    elif "uptime_ms" in connection:
        uptime_ms = _nonnegative_int(connection["uptime_ms"])
        if uptime_ms is not None and uptime_ms > 0:
            pool_connected = True
    else:
        uptime = _nonnegative_int(connection.get("uptime"))
        if uptime is not None and uptime > 0:
            pool_connected = True

    return MinerSnapshot(
        api_available=True,
        hashrate_10s=_hashrate(totals, 0),
        hashrate_60s=_hashrate(totals, 1),
        hashrate_15m=_hashrate(totals, 2),
        accepted=accepted,
        rejected=rejected,
        uptime_seconds=_nonnegative_int(payload.get("uptime")),
        pool_connected=pool_connected,
    )


class XmrigMonitor:
    """A fixed-loopback, read-only API client using the Python standard library."""

    def __init__(
        self,
        *,
        port: int = DEFAULT_API_PORT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        access_token: str | None = None,
    ) -> None:
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        if access_token is not None and (
            not isinstance(access_token, str)
            or not access_token
            or any(ord(c) < 33 or ord(c) > 126 for c in access_token)
        ):
            raise ValueError("invalid API access token")
        self._url = f"http://127.0.0.1:{port}/2/summary"
        self._timeout = float(timeout)
        self._access_token = access_token

    def poll(self) -> MinerSnapshot:
        """Return unavailable on a failed poll, without exposing response contents."""
        headers = {"Accept": "application/json"}
        if self._access_token is not None:
            headers["Authorization"] = f"Bearer {self._access_token}"
        request = urllib.request.Request(self._url, headers=headers, method="GET")
        # Disable proxy handling and HTTP redirects. Never send credentials to
        # a different host, even if a local endpoint responds with Location.
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirectHandler(),
        )
        try:
            with opener.open(request, timeout=self._timeout) as response:
                if response.status != 200:
                    return MinerSnapshot(False, error="http_error")
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    return MinerSnapshot(False, error="response_too_large")
            payload = json.loads(body.decode("utf-8"))
            return parse_summary(payload)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            return MinerSnapshot(False, error="api_unavailable")
        except (ValueError, UnicodeError, json.JSONDecodeError):
            return MinerSnapshot(False, error="invalid_json")


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
