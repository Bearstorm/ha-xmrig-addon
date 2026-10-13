"""Persist requested mining state outside MQTT and outside the mining core.

The add-on data directory survives container replacement. JSON writes use a
private temporary file and atomic os.replace. A damaged file fails closed OFF.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

DEFAULT_STATE_PATH = Path("/data/xmrig_state.json")


class StateStoreError(Exception):
    pass


class MiningStateStore:
    def __init__(self, path: Path = DEFAULT_STATE_PATH) -> None:
        self.path = Path(path)

    def load(self) -> bool:
        """Absent file preserves legacy startup ON; invalid file fails OFF."""
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return True
        except OSError as exc:
            raise StateStoreError("Unable to read mining state") from None
        if len(raw) > 256:
            raise StateStoreError("Mining state exceeds maximum size")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise StateStoreError("Invalid mining state") from None
        if not isinstance(data, dict) or data != {"version": 1, "running": data.get("running")}:
            raise StateStoreError("Invalid mining state schema")
        if not isinstance(data["running"], bool):
            raise StateStoreError("Invalid mining state value")
        return data["running"]

    def save(self, running: bool) -> None:
        if not isinstance(running, bool):
            raise StateStoreError("Invalid mining state value")
        temp = None
        try:
            # /data is provided by Home Assistant, not created implicitly.
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix=".xmrig-state-",
                dir=self.path.parent, delete=False
            ) as stream:
                temp = stream.name
                os.fchmod(stream.fileno(), 0o600)
                json.dump({"version": 1, "running": running}, stream,
                          separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
            temp = None
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            raise StateStoreError("Unable to persist mining state") from None
        finally:
            if temp is not None:
                try:
                    os.unlink(temp)
                except OSError:
                    pass
