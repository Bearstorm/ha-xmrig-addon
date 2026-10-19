"""Unprivileged, best-effort Linux resource telemetry for the beta container.

Only /proc and cgroup v2 are read. No Supervisor API, privileged host access,
wallet, or additional Python dependency is required. Missing values are None.
CPU percentages follow conventional Linux top semantics: 100% = one core.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

MIB = 1024 * 1024


@dataclass(frozen=True)
class ResourceSnapshot:
    process_cpu_percent: float | None = None
    process_ram_mib: float | None = None
    process_ram_peak_mib: float | None = None
    process_threads: int | None = None
    process_cpu_seconds: float | None = None
    container_cpu_percent: float | None = None
    container_ram_mib: float | None = None
    container_ram_percent: float | None = None
    container_net_rx_mib: float | None = None
    container_net_tx_mib: float | None = None
    container_disk_read_mib: float | None = None
    container_disk_write_mib: float | None = None


def _read_text(path: Path, *, limit: int = 65536) -> str | None:
    try:
        with path.open("r", encoding="ascii") as stream:
            text = stream.read(limit + 1)
        return text if len(text) <= limit else None
    except (OSError, UnicodeError):
        return None


def _unsigned(value: str | None) -> int | None:
    if value is None or not re.fullmatch(r"[0-9]{1,20}", value):
        return None
    return int(value)


def _key_values(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    data = _read_text(path)
    if data is None:
        return result
    for line in data.splitlines():
        bits = line.split()
        if len(bits) == 2:
            number = _unsigned(bits[1])
            if number is not None:
                result[bits[0].rstrip(":")] = number
    return result


def _proc_stat(path: Path) -> tuple[int, int, int] | None:
    data = _read_text(path, limit=4096)
    if data is None:
        return None
    # The comm field can contain spaces and closing parentheses.
    end = data.rfind(")")
    if end < 0:
        return None
    fields = data[end + 1:].split()
    # fields[0] is stat field 3 (state).
    if len(fields) < 20:
        return None
    try:
        user_ticks = int(fields[11])
        system_ticks = int(fields[12])
        start_ticks = int(fields[19])
    except ValueError:
        return None
    if min(user_ticks, system_ticks, start_ticks) < 0:
        return None
    return user_ticks + system_ticks, start_ticks, len(fields)


def _proc_status(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    data = _read_text(path, limit=16384)
    if data is None:
        return values
    for line in data.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        bits = raw.split()
        number = _unsigned(bits[0]) if bits else None
        if number is not None and key in ("VmRSS", "VmHWM", "Threads"):
            values[key] = number
    return values


def _network(path: Path) -> tuple[int, int] | None:
    data = _read_text(path)
    if data is None:
        return None
    rx = tx = 0
    found = False
    for line in data.splitlines()[2:]:
        if ":" not in line:
            continue
        interface, raw = line.rsplit(":", 1)
        if interface.strip() == "lo":
            continue
        bits = raw.split()
        if len(bits) < 16:
            continue
        received = _unsigned(bits[0])
        sent = _unsigned(bits[8])
        if received is not None and sent is not None:
            rx += received
            tx += sent
            found = True
    return (rx, tx) if found else None


def _io(path: Path) -> tuple[int, int] | None:
    data = _read_text(path)
    if data is None:
        return None
    read = written = 0
    found = False
    for line in data.splitlines():
        fields = dict(part.split("=", 1) for part in line.split()[1:] if "=" in part)
        r = _unsigned(fields.get("rbytes"))
        w = _unsigned(fields.get("wbytes"))
        if r is not None and w is not None:
            read += r
            written += w
            found = True
    return (read, written) if found else None


class ResourceMonitor:
    """Sample one child process plus the current container; never raises on absent stats."""

    def __init__(self, *, proc: Path = Path("/proc"),
                 cgroup: Path = Path("/sys/fs/cgroup"),
                 clock=time.monotonic) -> None:
        self._proc = Path(proc)
        self._cgroup = Path(cgroup)
        self._clock = clock
        self._ticks = os.sysconf("SC_CLK_TCK")
        self._last_process: tuple[int, int, int, float] | None = None
        self._last_container: tuple[int, float] | None = None

    def poll(self, pid: int | None) -> ResourceSnapshot:
        now = self._clock()
        process_cpu = process_ram = process_peak = None
        process_threads = process_seconds = None
        if isinstance(pid, int) and pid > 0:
            stat = _proc_stat(self._proc / str(pid) / "stat")
            status = _proc_status(self._proc / str(pid) / "status")
            if stat is not None:
                ticks, start, _ = stat
                process_seconds = round(ticks / self._ticks, 3)
                previous = self._last_process
                if previous is not None and previous[:2] == (pid, start):
                    dt = now - previous[3]
                    delta = ticks - previous[2]
                    if dt > 0 and delta >= 0:
                        process_cpu = round(100 * delta / self._ticks / dt, 2)
                self._last_process = (pid, start, ticks, now)
            else:
                self._last_process = None
            process_ram = round(status["VmRSS"] / 1024, 2) if "VmRSS" in status else None
            process_peak = round(status["VmHWM"] / 1024, 2) if "VmHWM" in status else None
            process_threads = status.get("Threads")
        else:
            self._last_process = None

        cpu = _key_values(self._cgroup / "cpu.stat").get("usage_usec")
        container_cpu = None
        if cpu is not None:
            previous = self._last_container
            if previous is not None:
                delta = cpu - previous[0]
                dt = now - previous[1]
                if delta >= 0 and dt > 0:
                    container_cpu = round(delta / 1_000_000 / dt * 100, 2)
            self._last_container = (cpu, now)
        else:
            self._last_container = None

        used = _unsigned((_read_text(self._cgroup / "memory.current") or "").strip())
        maximum = _unsigned((_read_text(self._cgroup / "memory.max") or "").strip())
        network = _network(self._proc / "net" / "dev")
        disk = _io(self._cgroup / "io.stat")
        return ResourceSnapshot(
            process_cpu_percent=process_cpu,
            process_ram_mib=process_ram,
            process_ram_peak_mib=process_peak,
            process_threads=process_threads,
            process_cpu_seconds=process_seconds,
            container_cpu_percent=container_cpu,
            container_ram_mib=round(used / MIB, 2) if used is not None else None,
            container_ram_percent=round(used / maximum * 100, 2) if used is not None and maximum else None,
            container_net_rx_mib=round(network[0] / MIB, 3) if network else None,
            container_net_tx_mib=round(network[1] / MIB, 3) if network else None,
            container_disk_read_mib=round(disk[0] / MIB, 3) if disk else None,
            container_disk_write_mib=round(disk[1] / MIB, 3) if disk else None,
        )
