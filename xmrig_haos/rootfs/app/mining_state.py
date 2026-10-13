"""Persist requested mining state outside MQTT and outside the mining core.

The add-on data directory survives container replacement. JSON writes use a
private temporary file and atomic os.replace. A damaged file fails closed OFF.
"""
from __future__ import annotations

import json
import os
import stat
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
        if not isinstance(data, dict) or set(data) != {"version", "running"} or data["version"] != 1:
            raise StateStoreError("Invalid mining state schema")
        if not isinstance(data["running"], bool):
            raise StateStoreError("Invalid mining state value")
        return data["running"]


    @property
    def guard_path(self) -> Path:
        return self.path.with_name(self.path.name + ".armed")

    def guard_exists(self) -> bool:
        """A left-behind arm marker means unexpected shutdown: fail closed."""
        try:
            info = self.guard_path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise StateStoreError("Invalid mining startup guard")
            if self.guard_path.read_bytes() != b"armed\n":
                raise StateStoreError("Invalid mining startup guard")
            return True
        except FileNotFoundError:
            return False
        except OSError:
            raise StateStoreError("Unable to check mining startup guard") from None

    def arm(self) -> None:
        """Persist a crash guard before allowing the miner to start."""
        temp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".xmrig-armed-",
                dir=self.path.parent, delete=False
            ) as stream:
                temp = stream.name
                os.fchmod(stream.fileno(), 0o600)
                stream.write(b"armed\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.guard_path)
            temp = None
            self._sync_directory()
        except OSError:
            raise StateStoreError("Unable to arm mining startup guard") from None
        finally:
            if temp is not None:
                try:
                    os.unlink(temp)
                except OSError:
                    pass

    def disarm(self) -> None:
        """Remove guard only after a verified graceful shutdown or saved OFF."""
        try:
            self.guard_path.unlink(missing_ok=True)
            self._sync_directory()
        except OSError:
            raise StateStoreError("Unable to clear mining startup guard") from None

    def _sync_directory(self) -> None:
        directory_fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

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
            self._sync_directory()
        except OSError:
            raise StateStoreError("Unable to persist mining state") from None
        finally:
            if temp is not None:
                try:
                    os.unlink(temp)
                except OSError:
                    pass
