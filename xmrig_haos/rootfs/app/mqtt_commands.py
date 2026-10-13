"""Bounded MQTT command mailbox; never manages XMRig from an MQTT callback.

Only exact non-retained ON/OFF messages can enter the mailbox. Controller
consumes requests from its own event loop. No broker reconnect replays commands.
"""
from __future__ import annotations

import threading


class CommandMailbox:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: str | None = None

    def submit(self, topic: str, payload: bytes, *, retained: bool = False,
               expected_topic: str = "xmrig_haos/command") -> bool:
        if retained or topic != expected_topic or not isinstance(payload, bytes):
            return False
        if payload not in (b"ON", b"OFF"):
            return False
        with self._lock:
            # Latest requested state wins; avoids an unbounded command queue.
            self._pending = payload.decode("ascii")
        return True

    def clear(self) -> None:
        """Discard commands from a disconnected MQTT session."""
        with self._lock:
            self._pending = None

    def take(self) -> str | None:
        with self._lock:
            value = self._pending
            self._pending = None
            return value
