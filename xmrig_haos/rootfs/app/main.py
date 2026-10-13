"""XMRig HAOS Safe process controller.

This module does not require MQTT, Supervisor, or access to host processes.
Until Dockerfile is migrated, the existing run.sh remains the add-on entrypoint.
"""

from __future__ import annotations

import logging
import signal
import threading
from collections.abc import Callable
from typing import Protocol

from .config import ConfigError, load_config
from .miner_manager import MinerError, MinerManager, MinerState

LOG = logging.getLogger("xmrig-controller")
POLL_INTERVAL_SECONDS = 1.0


class ManagerProtocol(Protocol):
    @property
    def state(self) -> MinerState: ...

    @property
    def last_error(self) -> str | None: ...

    @property
    def retry_at(self) -> float | None: ...

    @property
    def desired_running(self) -> bool: ...

    def start(self) -> bool: ...
    def reconcile(self) -> MinerState: ...
    def shutdown(self, timeout: float = 10.0) -> None: ...


class Controller:
    """Own the manager and coordinate an orderly process shutdown."""

    def __init__(
        self,
        manager: ManagerProtocol,
        *,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        stop_event: threading.Event | None = None,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self._manager = manager
        self._poll_interval = poll_interval
        self._stop_event = stop_event if stop_event is not None else threading.Event()
        self._shutdown_requested = False

    def request_shutdown(self) -> None:
        self._shutdown_requested = True
        self._stop_event.set()

    def run(self) -> int:
        """Run until signalled or retries are exhausted; always reap miner."""
        exit_code = 0
        try:
            self._manager.start()
            while not self._stop_event.is_set():
                state = self._manager.reconcile()
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
            # Do not log underlying exception data, which can contain credentials.
            LOG.error("XMRig process management failed")
            exit_code = 1
        finally:
            try:
                self._manager.shutdown()
            except (MinerError, OSError):
                LOG.error("XMRig shutdown failed")
                exit_code = 1
        return exit_code


def main(
    *,
    config_loader: Callable = load_config,
    manager_factory: Callable = MinerManager,
    install_signals: bool = True,
) -> int:
    """Wire production dependencies while allowing isolated unit testing."""
    logging.basicConfig(level=logging.INFO, format="[xmrig-controller] %(message)s")
    try:
        config = config_loader()
    except (ConfigError, OSError):
        LOG.error("Invalid or unreadable add-on configuration")
        return 1

    controller = Controller(manager_factory(config))
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
    raise SystemExit(main())
