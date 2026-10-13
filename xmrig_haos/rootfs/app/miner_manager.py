"""Manage a single XMRig subprocess without MQTT or Home Assistant dependencies.

The caller owns the event loop: call reconcile() periodically, and shutdown()
when the add-on exits. The manager never logs or renders the wallet value.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

try:
    from .config import MinerConfig
except ImportError:
    # Running as a script is intentionally unsupported; import as a package.
    raise


class MinerError(RuntimeError):
    """A process-control failure, without credentials or command-line details."""


class MinerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(frozen=True)
class MemoryPaths:
    meminfo: Path = Path("/proc/meminfo")
    cgroup_max: Path = Path("/sys/fs/cgroup/memory.max")
    cgroup_current: Path = Path("/sys/fs/cgroup/memory.current")


@dataclass(frozen=True)
class RestartPolicy:
    delays: tuple[float, ...] = (5.0, 15.0, 30.0)
    stable_seconds: float = 300.0

    def __post_init__(self) -> None:
        if not self.delays or any(d < 0 for d in self.delays):
            raise ValueError("restart delays must be nonempty and nonnegative")
        if self.stable_seconds <= 0:
            raise ValueError("stable_seconds must be positive")


def _read_decimal(path: Path, *, max_digits: int = 18) -> Optional[int]:
    try:
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return None
    if not re.fullmatch(r"[0-9]+", value, re.ASCII) or len(value) > max_digits:
        return None
    return int(value, 10)


def available_memory_bytes(paths: MemoryPaths = MemoryPaths()) -> int:
    """Mirror run.sh's MemAvailable/cgroup-v2 estimate conservatively."""
    available = 0
    try:
        with paths.meminfo.open(encoding="ascii") as stream:
            for line in stream:
                match = re.fullmatch(r"MemAvailable:\s*([0-9]+)\s+kB\s*", line)
                if match and len(match.group(1)) <= 15:
                    available = int(match.group(1), 10) * 1024
                if line.startswith("MemAvailable:"):
                    break
    except (OSError, UnicodeError):
        pass

    maximum = _read_decimal(paths.cgroup_max)
    current = _read_decimal(paths.cgroup_current)
    if maximum is not None and current is not None:
        cgroup_available = max(0, maximum - current)
        if available == 0 or cgroup_available < available:
            available = cgroup_available
    return available


def randomx_mode(memory_bytes: int) -> str:
    return "fast" if memory_bytes >= 3 * 1024**3 else "light"


def build_xmrig_args(config: MinerConfig, memory_bytes: int) -> list[str]:
    """Preserve the options used by the existing HAOS run.sh."""
    args = [
        "--url", config.pool_url,
        "--user", config.wallet,
        "--pass", config.worker,
        f"--threads={config.threads}",
        f"--cpu-priority={config.priority}",
        "--randomx-wrmsr=-1",
        "--randomx-no-rdmsr",
        "--no-huge-pages",
        "--keepalive",
        f"--randomx-mode={randomx_mode(memory_bytes)}",
    ]
    if config.tls_enabled:
        args.append("--tls")
    return args


class MinerManager:
    """Own a single XMRig child and manage bounded crash recovery.

    start() is an explicit user/controller request. reconcile() polls for crashes
    and performs scheduled retries. stop() disables auto-restart, and shutdown()
    is its idempotent alias for add-on teardown.
    """

    def __init__(
        self,
        config: MinerConfig,
        *,
        binary: str = "/usr/bin/xmrig",
        memory_paths: MemoryPaths = MemoryPaths(),
        restart_policy: RestartPolicy = RestartPolicy(),
        clock: Callable[[], float] = time.monotonic,
        popen: Callable[..., subprocess.Popen] = subprocess.Popen,
    ) -> None:
        if not os.path.isabs(binary):
            raise ValueError("XMRig binary path must be absolute")
        self._config = config
        self._binary = binary
        self._memory_paths = memory_paths
        self._policy = restart_policy
        self._clock = clock
        self._popen = popen
        self._process: Optional[subprocess.Popen] = None
        self._state = MinerState.STOPPED
        self._desired_running = False
        self._retry_count = 0
        self._retry_at: Optional[float] = None
        self._started_at: Optional[float] = None
        self._last_exit_code: Optional[int] = None
        self._last_error: Optional[str] = None

    @property
    def state(self) -> MinerState:
        return self._state

    @property
    def pid(self) -> Optional[int]:
        return self._process.pid if self._process is not None else None

    @property
    def last_exit_code(self) -> Optional[int]:
        return self._last_exit_code

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def retry_at(self) -> Optional[float]:
        return self._retry_at

    @property
    def desired_running(self) -> bool:
        return self._desired_running

    def _launch(self) -> bool:
        if self._process is not None:
            raise MinerError("XMRig process is already owned")
        self._state = MinerState.STARTING
        args = [self._binary, *build_xmrig_args(
            self._config, available_memory_bytes(self._memory_paths)
        )]
        try:
            self._process = self._popen(
                args,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError:
            # Never include exception text: an exception could expose argv.
            self._state = MinerState.ERROR
            self._last_error = "Unable to start XMRig process"
            self._handle_crash(self._clock())
            return False
        self._started_at = self._clock()
        self._retry_at = None
        self._state = MinerState.RUNNING
        self._last_error = None
        return True

    def start(self) -> bool:
        """Request mining. Returns False when a process/retry already exists."""
        if self._desired_running:
            return False
        if self._process is not None:
            return False
        self._desired_running = True
        self._retry_count = 0
        self._retry_at = None
        return self._launch()

    def _handle_crash(self, now: float) -> None:
        if not self._desired_running:
            self._state = MinerState.STOPPED
            return
        if self._retry_count >= len(self._policy.delays):
            self._desired_running = False
            self._retry_at = None
            self._state = MinerState.ERROR
            self._last_error = "XMRig restart limit reached"
            return
        delay = self._policy.delays[self._retry_count]
        self._retry_count += 1
        self._retry_at = now + delay
        self._state = MinerState.ERROR

    def reconcile(self) -> MinerState:
        """Poll process and perform due retries. Must be called periodically."""
        now = self._clock()
        if self._process is not None:
            code = self._process.poll()
            if code is None:
                if (
                    self._started_at is not None
                    and now - self._started_at >= self._policy.stable_seconds
                ):
                    self._retry_count = 0
                return self._state
            self._last_exit_code = code
            self._process = None
            self._started_at = None
            self._last_error = "XMRig process exited unexpectedly"
            self._handle_crash(now)
        if (
            self._desired_running
            and self._process is None
            and self._retry_at is not None
            and now >= self._retry_at
        ):
            self._launch()
        return self._state

    def stop(self, timeout: float = 10.0) -> None:
        """Disable retries and terminate the owned XMRig process safely."""
        if timeout < 0:
            raise ValueError("timeout must be nonnegative")
        self._desired_running = False
        self._retry_at = None
        self._retry_count = 0
        process = self._process
        if process is None:
            self._state = MinerState.STOPPED
            return
        self._state = MinerState.STOPPING
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            else:
                process.wait()
        except OSError as exc:
            self._state = MinerState.ERROR
            self._last_error = "Unable to stop XMRig process"
            raise MinerError(self._last_error) from exc
        self._last_exit_code = process.returncode
        self._process = None
        self._started_at = None
        self._state = MinerState.STOPPED

    def shutdown(self, timeout: float = 10.0) -> None:
        self.stop(timeout=timeout)
