
"""Configuration validation for the XMRig HAOS Safe controller.

This module has no MQTT, Home Assistant, or XMRig process dependencies.
"""

from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

DEFAULT_CONFIG_PATH = Path("/data/options.json")
DEFAULT_POOL = "pool.supportxmr.com"
DEFAULT_PORT = 443
DEFAULT_WORKER = "HA"
DEFAULT_THREADS = 2
DEFAULT_PRIORITY = 2
DEFAULT_TLS_MODE = "auto"

SUPPORTED_TLS_MODES = frozenset({
    "auto",
    "enabled",
    "disabled",
})

_INTEGER_PATTERN = re.compile(
    r"^[0-9]+$",
    re.ASCII,
)

_HOST_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]+$",
    re.ASCII,
)

_SCHEME_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9+.-]*)://"
)


class ConfigError(ValueError):
    """Invalid miner configuration, safe to display without credentials."""


def _string(
    value: Any,
    name: str,
    *,
    allow_empty: bool = False,
    max_length: int = 255,
) -> str:
    if not isinstance(value, str):
        raise ConfigError(
            f"{name} must be a string"
        )

    if (
        (not value and not allow_empty)
        or len(value) > max_length
    ):
        raise ConfigError(
            f"{name} must contain "
            f"{0 if allow_empty else 1} "
            f"to {max_length} characters"
        )

    if any(
        ord(char) < 32 or ord(char) == 127
        for char in value
    ):
        raise ConfigError(
            f"{name} contains control characters"
        )

    return value


def _integer(
    value: Any,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool):
        raise ConfigError(
            f"{name} must be an integer "
            f"from {minimum} to {maximum}"
        )

    if isinstance(value, int):
        number = value

    elif (
        isinstance(value, str)
        and _INTEGER_PATTERN.fullmatch(value)
        and len(value) <= 16
    ):
        number = int(value, 10)

    else:
        raise ConfigError(
            f"{name} must be an integer "
            f"from {minimum} to {maximum}"
        )

    if not minimum <= number <= maximum:
        raise ConfigError(
            f"{name} must be between "
            f"{minimum} and {maximum}"
        )

    return number


def _pool_host(pool: str) -> str:
    """Normalize host or host:port; dedicated port option always wins."""

    match = _SCHEME_PATTERN.match(pool)

    if match:
        pool = pool[match.end():]

    pool = pool.removesuffix("/")

    if (
        not pool
        or any(c.isspace() for c in pool)
        or any(c in pool for c in "/@?#\\")
    ):
        raise ConfigError(
            "pool has an invalid address"
        )

    if pool.startswith("["):
        match = re.fullmatch(
            r"\[([^\]]+)\](?::([0-9]+))?",
            pool,
            re.ASCII,
        )

        if not match:
            raise ConfigError(
                "pool has an invalid bracketed IPv6 address"
            )

        try:
            ipaddress.IPv6Address(match.group(1))
        except ValueError as exc:
            raise ConfigError(
                "pool has an invalid IPv6 address"
            ) from exc

        return f"[{match.group(1)}]"

    if pool.count(":") > 1:
        raise ConfigError(
            "IPv6 pool addresses require brackets"
        )

    if ":" in pool:
        pool, embedded_port = pool.split(":", 1)

        if (
            not embedded_port
            or not embedded_port.isascii()
            or not embedded_port.isdigit()
        ):
            raise ConfigError(
                "pool contains an invalid embedded port"
            )

        _integer(
            embedded_port,
            "embedded pool port",
            1,
            65535,
        )

    if not _HOST_PATTERN.fullmatch(pool):
        raise ConfigError(
            "pool has an invalid hostname"
        )

    return pool


@dataclass(frozen=True)
class MinerConfig:
    pool: str
    port: int
    wallet: str = field(repr=False)
    worker: str = DEFAULT_WORKER
    threads: int = DEFAULT_THREADS
    priority: int = DEFAULT_PRIORITY
    tls_mode: str = DEFAULT_TLS_MODE

    @property
    def pool_host(self) -> str:
        return _pool_host(self.pool)

    @property
    def pool_url(self) -> str:
        return f"{self.pool_host}:{self.port}"

    @property
    def tls_enabled(self) -> bool:
        return (
            self.tls_mode == "enabled"
            or (
                self.tls_mode == "auto"
                and self.port == 443
            )
        )


def parse_config(
    options: Mapping[str, Any],
) -> MinerConfig:
    """Validate an options.json mapping.

    Additional future add-on settings are ignored.
    """

    if not isinstance(options, Mapping):
        raise ConfigError(
            "configuration must be a JSON object"
        )

    pool = _string(
        options.get("pool", DEFAULT_POOL),
        "pool",
        max_length=255,
    )

    _pool_host(pool)

    wallet = _string(
        options.get("wallet", ""),
        "wallet",
        max_length=512,
    )

    worker = _string(
        options.get("worker", DEFAULT_WORKER),
        "worker",
        max_length=64,
    )

    port = _integer(
        options.get("port", DEFAULT_PORT),
        "port",
        1,
        65535,
    )

    threads = _integer(
        options.get("threads", DEFAULT_THREADS),
        "threads",
        1,
        256,
    )

    priority = _integer(
        options.get("priority", DEFAULT_PRIORITY),
        "priority",
        0,
        5,
    )

    tls_mode = _string(
        options.get("tls_mode", DEFAULT_TLS_MODE),
        "tls_mode",
        max_length=8,
    )

    if tls_mode not in SUPPORTED_TLS_MODES:
        raise ConfigError(
            "tls_mode must be auto, enabled, or disabled"
        )

    return MinerConfig(
        pool,
        port,
        wallet,
        worker,
        threads,
        priority,
        tls_mode,
    )


def load_config(
    path: str | Path = DEFAULT_CONFIG_PATH,
) -> MinerConfig:
    """Read add-on options without exposing their values in errors."""

    try:
        with Path(path).open(
            "r",
            encoding="utf-8",
        ) as stream:
            options = json.load(stream)

    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ConfigError(
            "configuration file cannot be read as valid JSON"
        ) from exc

    return parse_config(options)
