"""XMRig HAOS Safe controller with independent read-only HTTP telemetry.

The miner lifecycle never depends on MQTT or HTTP monitoring availability.
The existing run.sh stays the entrypoint until a separately tested migration.
"""
from __future__ import annotations

import logging
import signal
import time
import threading
from collections.abc import Callable
from typing import Protocol

from .config import ConfigError, load_config
from .miner_manager import MinerError, MinerManager, MinerState
from .mining_state import MiningStateStore, StateStoreError
from .xmrig_monitor import MinerSnapshot, XmrigMonitor
from .resource_monitor import ResourceMonitor
from .thermal import ThermalGuard

LOG = logging.getLogger("xmrig-controller")
POLL_INTERVAL_SECONDS = 1.0
MONITOR_INTERVAL_SECONDS = 5.0


class ManagerProtocol(Protocol):
    @property
    def state(self) -> MinerState: ...
    @property
    def pid(self) -> int | None: ...
    @property
    def last_error(self) -> str | None: ...
    @property
    def retry_at(self) -> float | None: ...
    @property
    def desired_running(self) -> bool: ...
    def start(self) -> bool: ...
    def stop(self, timeout: float = 10.0) -> None: ...
    def reconcile(self) -> MinerState: ...
    def shutdown(self, timeout: float = 10.0) -> None: ...


class MonitorProtocol(Protocol):
    def poll(self) -> MinerSnapshot: ...


class PublisherProtocol(Protocol):
    def start(self) -> bool: ...
    def publish(self, snapshot: MinerSnapshot, *, process_running: bool) -> bool: ...
    def close(self) -> None: ...


class Controller:
    """Supervise one miner and optionally sample its metrics in a worker thread."""

    def __init__(
        self,
        manager: ManagerProtocol,
        *,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        stop_event: threading.Event | None = None,
        monitor: MonitorProtocol | None = None,
        monitor_interval: float = MONITOR_INTERVAL_SECONDS,
        publisher: PublisherProtocol | None = None,
        state_store: MiningStateStore | None = None,
        resource_monitor: ResourceMonitor | None = None,
        thermal_guard: ThermalGuard | None = None,
    ) -> None:
        if poll_interval <= 0 or monitor_interval <= 0:
            raise ValueError("poll intervals must be positive")
        self._manager = manager
        self._poll_interval = poll_interval
        self._stop_event = stop_event if stop_event is not None else threading.Event()
        self._monitor = monitor
        self._publisher = publisher
        self._state_store = state_store
        self._resource_monitor = resource_monitor
        self._thermal_guard = thermal_guard
        self._thermal_next = 0.0
        self._thermal_latched = False
        self._resource_thread: threading.Thread | None = None
        self._armed_by_this_session = False
        self._failed_off_persistence = False
        self._monitor_interval = monitor_interval
        self._monitor_stop = threading.Event()
        self._monitor_wake = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._snapshot_lock = threading.Lock()
        self._snapshot = MinerSnapshot(False, error="miner_not_running")
        self._current_pid: int | None = None
        self._generation = 0

    @property
    def snapshot(self) -> MinerSnapshot:
        with self._snapshot_lock:
            return self._snapshot

    def request_shutdown(self) -> None:
        self._stop_event.set()
        self._monitor_stop.set()
        self._monitor_wake.set()

    def _update_process(self, state: MinerState) -> None:
        pid = self._manager.pid if state == MinerState.RUNNING else None
        with self._snapshot_lock:
            if pid == self._current_pid:
                return
            self._current_pid = pid
            self._generation += 1
            self._snapshot = MinerSnapshot(
                False, error="awaiting_api" if pid is not None else "miner_not_running"
            )
        self._monitor_wake.set()
        if pid is None:
            self._publish_snapshot(MinerSnapshot(False, error="miner_not_running"), process_running=False)

    def _monitor_loop(self) -> None:
        while not self._monitor_stop.is_set():
            with self._snapshot_lock:
                pid = self._current_pid
                generation = self._generation
            if pid is None:
                self._monitor_wake.wait(timeout=0.2)
                self._monitor_wake.clear()
                continue
            try:
                assert self._monitor is not None
                sample = self._monitor.poll()
                if not isinstance(sample, MinerSnapshot):
                    sample = MinerSnapshot(False, error="invalid_monitor_result")
            except Exception:
                # Never disclose HTTP error bodies, credentials, or URLs.
                LOG.warning("XMRig telemetry polling failed")
                sample = MinerSnapshot(False, error="monitor_error")
            publish_snapshot = False
            with self._snapshot_lock:
                if (
                    not self._monitor_stop.is_set()
                    and self._current_pid == pid
                    and self._generation == generation
                ):
                    self._snapshot = sample
                    publish_snapshot = True
            if publish_snapshot:
                self._publish_snapshot(sample, process_running=True)
            self._monitor_wake.wait(timeout=self._monitor_interval)
            self._monitor_wake.clear()

    def _resources_loop(self) -> None:
        """Publish cgroup stats even while mining is OFF; fail closed on errors."""
        while not self._monitor_stop.is_set():
            try:
                with self._snapshot_lock:
                    pid = self._current_pid
                assert self._resource_monitor is not None
                sample = self._resource_monitor.poll(pid)
                publish = getattr(self._publisher, "publish_resources", None)
                if callable(publish):
                    publish(sample)
            except Exception:
                LOG.warning("Optional resource telemetry failed")
            self._monitor_stop.wait(self._monitor_interval)

    def _publish_snapshot(self, snapshot: MinerSnapshot, *, process_running: bool) -> None:
        if self._publisher is None:
            return
        try:
            self._publisher.publish(snapshot, process_running=process_running)
        except Exception:
            LOG.warning("Optional MQTT publisher failed; mining continues")

    def _thermal_check(self, force=False):
        guard = self._thermal_guard
        if guard is None or not guard.enabled:
            return True
        if self._thermal_latched:
            return False
        now = time.monotonic()
        if not force and now < self._thermal_next:
            return True
        self._thermal_next = now + 30
        safe, reason, temperature = guard.check()
        if safe:
            return True
        self._thermal_latched = True
        LOG.warning("Thermal protection tripped: %s", reason)
        if self._state_store is not None:
            try:
                self._state_store.save(False)
            except StateStoreError:
                self._failed_off_persistence = True
                LOG.warning("Thermal OFF persistence failed; startup guard retained")
        if self._manager.desired_running:
            self._manager.stop()
            self._update_process(MinerState.STOPPED)
        if self._state_store is not None and not self._failed_off_persistence:
            try:
                self._state_store.disarm()
                self._armed_by_this_session = False
            except StateStoreError:
                LOG.warning("Thermal guard marker retained")
        guard.notify(reason, temperature)
        return False

    def _apply_mqtt_command(self) -> None:
        """Apply one bounded MQTT request only from the Controller thread."""
        commands = getattr(self._publisher, "commands", None)
        if commands is None:
            return
        try:
            command = commands.take()
        except Exception:
            LOG.warning("MQTT command mailbox failed; mining continues")
            return
        if command == "OFF":
            saved_off = True
            if self._state_store is not None:
                try:
                    self._state_store.save(False)
                except StateStoreError:
                    saved_off = False
                    self._failed_off_persistence = True
                    LOG.warning("Unable to persist OFF state; restart guard remains armed")
            if self._manager.desired_running:
                self._manager.stop()
                self._update_process(MinerState.STOPPED)
            if saved_off and self._state_store is not None:
                try:
                    self._state_store.disarm()
                    self._armed_by_this_session = False
                    self._failed_off_persistence = False
                except StateStoreError:
                    LOG.warning("Unable to clear startup guard; next startup will remain OFF")
        elif command == "ON" and not self._manager.desired_running:
            if not self._thermal_check(force=True):
                LOG.warning("Mining ON rejected by thermal protection")
                return
            if self._state_store is not None:
                try:
                    # Arm guard first, before storing ON or spawning a process.
                    self._state_store.arm()
                    self._armed_by_this_session = True
                    self._state_store.save(True)
                except StateStoreError:
                    LOG.warning("Unable to safely arm mining; miner remains stopped")
                    return
            self._manager.start()
            self._update_process(self._manager.state)

    def run(self) -> int:
        """Run until signalled or retries are exhausted; always reap miner."""
        exit_code = 0
        try:
            if self._publisher is not None and not self._stop_event.is_set():
                try:
                    self._publisher.start()
                except Exception:
                    LOG.warning("Optional MQTT startup failed; mining continues")
            if self._monitor is not None and not self._stop_event.is_set():
                self._monitor_thread = threading.Thread(
                    target=self._monitor_loop, name="xmrig-telemetry", daemon=True
                )
                self._monitor_thread.start()
            if (self._resource_monitor is not None and self._publisher is not None
                    and not self._stop_event.is_set()):
                self._resource_thread = threading.Thread(
                    target=self._resources_loop, name="xmrig-resources", daemon=True
                )
                self._resource_thread.start()
            if not self._stop_event.is_set():
                should_start = True
                if self._state_store is not None:
                    try:
                        should_start = self._state_store.load()
                        if self._state_store.guard_exists():
                            LOG.warning("Unclean previous shutdown; mining remains OFF")
                            should_start = False
                        if should_start:
                            # A crash while running leaves the guard in place.
                            self._state_store.arm()
                            self._armed_by_this_session = True
                    except StateStoreError:
                        LOG.warning("Unsafe mining state or storage; starting safely OFF")
                        should_start = False
                if should_start and self._thermal_check(force=True):
                    self._manager.start()
                else:
                    self._publish_snapshot(
                        MinerSnapshot(False, error="miner_not_running"),
                        process_running=False,
                    )
                self._update_process(self._manager.state)
            while not self._stop_event.is_set():
                self._thermal_check()
                self._apply_mqtt_command()
                state = self._manager.reconcile()
                self._update_process(state)
                if (
                    state == MinerState.ERROR
                    and not self._manager.desired_running
                    and self._manager.retry_at is None
                ):
                    LOG.error("XMRig stopped: recovery attempts exhausted")
                    exit_code = 1
                    break
                self._stop_event.wait(self._poll_interval)
        except (MinerError, OSError):
            LOG.error("XMRig process management failed")
            exit_code = 1
        finally:
            self._monitor_stop.set()
            self._monitor_wake.set()
            try:
                self._manager.shutdown()
            except (MinerError, OSError):
                LOG.error("XMRig shutdown failed")
                exit_code = 1
            self._update_process(MinerState.STOPPED)
            if self._resource_thread is not None:
                self._resource_thread.join(timeout=3.0)
                if self._resource_thread.is_alive():
                    LOG.error("Resource worker did not stop in time")
                    exit_code = 1
            if self._monitor_thread is not None:
                # Poll has a 2s timeout in production. A join bound avoids
                # hanging add-on shutdown if a custom monitor misbehaves.
                self._monitor_thread.join(timeout=3.0)
                if self._monitor_thread.is_alive():
                    LOG.error("Telemetry worker did not stop in time")
                    exit_code = 1
            with self._snapshot_lock:
                self._snapshot = MinerSnapshot(False, error="miner_not_running")
            if (
                self._state_store is not None
                and self._armed_by_this_session
                and not self._failed_off_persistence
                and self._stop_event.is_set()
                and exit_code == 0
            ):
                # Graceful shutdown preserves the previous ON preference.
                # A crash or failed OFF persistence must retain the guard.
                try:
                    if self._state_store.load():
                        self._state_store.disarm()
                        self._armed_by_this_session = False
                except StateStoreError:
                    LOG.warning("Startup guard retained; next startup will remain OFF")
            if self._publisher is not None:
                try:
                    self._publisher.close()
                except Exception:
                    LOG.warning("Optional MQTT shutdown failed")
        return exit_code


def main(
    *,
    config_loader: Callable = load_config,
    manager_factory: Callable = MinerManager,
    monitor_factory: Callable = XmrigMonitor,
    publisher_factory: Callable[[], PublisherProtocol | None] | None = None,
    state_store_factory: Callable[[], MiningStateStore] | None = None,
    resource_monitor_factory: Callable[[], ResourceMonitor] | None = None,
    install_signals: bool = True,
) -> int:
    """Wire production components; monitor failures never block mining."""
    logging.basicConfig(level=logging.INFO, format="[xmrig-controller] %(message)s")
    try:
        config = config_loader()
    except (ConfigError, OSError):
        LOG.error("Invalid or unreadable add-on configuration")
        return 1
    try:
        manager = manager_factory(config)
    except (ValueError, TypeError, OSError, MinerError):
        LOG.error("Unable to initialize XMRig process manager")
        return 1
    try:
        monitor = monitor_factory()
    except (ValueError, TypeError, OSError):
        LOG.warning("Unable to initialize telemetry; mining remains available")
        monitor = None
    publisher = None
    if publisher_factory is not None:
        try:
            publisher = publisher_factory()
        except Exception:
            LOG.warning("MQTT setup failed; mining remains available")
    state_store = None
    if state_store_factory is not None:
        try:
            state_store = state_store_factory()
        except Exception:
            LOG.warning("Mining state store unavailable; startup is blocked")
            return 1
    resource_monitor = None
    if resource_monitor_factory is not None:
        try:
            resource_monitor = resource_monitor_factory()
        except (OSError, ValueError):
            LOG.warning("Optional resource monitor unavailable")
    try:
        thermal_guard = ThermalGuard()
    except (OSError, ValueError, TypeError):
        LOG.error("Invalid thermal configuration; startup blocked")
        return 1
    controller = Controller(manager, monitor=monitor, publisher=publisher,
                            state_store=state_store, resource_monitor=resource_monitor,
                            thermal_guard=thermal_guard)
    previous_handlers: dict[signal.Signals, object] = {}
    try:
        if install_signals:
            for signum in (signal.SIGINT, signal.SIGTERM):
                previous_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, lambda _signum, _frame: controller.request_shutdown())
        return controller.run()
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    from .mqtt_runtime import load_mqtt_publisher

    raise SystemExit(main(publisher_factory=load_mqtt_publisher,
                          state_store_factory=MiningStateStore,
                          resource_monitor_factory=ResourceMonitor))
