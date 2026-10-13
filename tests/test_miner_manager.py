"""Process-independent tests of XMRig MinerManager."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "xmrig_haos" / "rootfs" / "app"

# Load config.py and miner_manager.py as one in-memory package, independent
# of whether __init__.py has already been added to the repository.
import types
pkg = types.ModuleType("xmrig_test_app")
pkg.__path__ = [str(APP_DIR)]
sys.modules[pkg.__name__] = pkg
for name in ("config", "miner_manager"):
    spec = importlib.util.spec_from_file_location(
        f"{pkg.__name__}.{name}", APP_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

config_module = sys.modules["xmrig_test_app.config"]
manager_module = sys.modules["xmrig_test_app.miner_manager"]
MinerManager = manager_module.MinerManager
MinerState = manager_module.MinerState
MemoryPaths = manager_module.MemoryPaths
RestartPolicy = manager_module.RestartPolicy
parse_config = config_module.parse_config


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeProcess:
    _next_pid = 100

    def __init__(self):
        FakeProcess._next_pid += 1
        self.pid = FakeProcess._next_pid
        self.returncode = None
        self.terminated = False
        self.killed = False
        self.timeout_on_wait = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.timeout_on_wait and not self.killed:
            raise subprocess.TimeoutExpired("fake-xmrig", timeout)
        if self.returncode is None:
            self.returncode = -15 if self.terminated else 0
        return self.returncode

    def crash(self, code=3):
        self.returncode = code


class FakeSpawner:
    def __init__(self):
        self.processes = []
        self.args = []
        self.fail = False

    def __call__(self, args, **kwargs):
        if self.fail:
            raise OSError("sensitive argv must not appear")
        self.args.append((args, kwargs))
        process = FakeProcess()
        self.processes.append(process)
        return process


class MinerManagerTests(unittest.TestCase):
    def setUp(self):
        self.config = parse_config({
            "pool": "pool.supportxmr.com",
            "port": 443,
            "wallet": "SECRET_WALLET",
            "worker": "HA",
            "threads": 2,
            "priority": 2,
            "tls_mode": "auto",
        })
        self.clock = FakeClock()
        self.spawner = FakeSpawner()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        meminfo = self.dir / "meminfo"
        meminfo.write_text("MemAvailable:    4000000 kB\n", encoding="ascii")
        cmax = self.dir / "max"
        cmax.write_text("max\n", encoding="ascii")
        ccurrent = self.dir / "current"
        ccurrent.write_text("100\n", encoding="ascii")
        self.paths = MemoryPaths(meminfo, cmax, ccurrent)
        self.manager = MinerManager(
            self.config,
            binary="/fake/xmrig",
            memory_paths=self.paths,
            clock=self.clock,
            popen=self.spawner,
        )

    def test_initial_state(self):
        self.assertEqual(self.manager.state, MinerState.STOPPED)
        self.assertIsNone(self.manager.pid)

    def test_start_and_pid(self):
        self.assertTrue(self.manager.start())
        self.assertEqual(self.manager.state, MinerState.RUNNING)
        self.assertEqual(self.manager.pid, self.spawner.processes[0].pid)

    def test_no_second_start(self):
        self.manager.start()
        self.assertFalse(self.manager.start())
        self.assertEqual(len(self.spawner.processes), 1)

    def test_command_retains_safe_flags(self):
        self.manager.start()
        args, kwargs = self.spawner.args[0]
        for flag in (
            "--randomx-wrmsr=-1", "--randomx-no-rdmsr",
            "--no-huge-pages", "--keepalive", "--tls", "--randomx-mode=fast"
        ):
            self.assertIn(flag, args)
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertTrue(kwargs["close_fds"])

    def test_stop_sends_sigterm(self):
        self.manager.start()
        proc = self.spawner.processes[0]
        self.manager.stop()
        self.assertTrue(proc.terminated)
        self.assertFalse(proc.killed)
        self.assertEqual(self.manager.state, MinerState.STOPPED)

    def test_stop_kills_after_timeout(self):
        self.manager.start()
        proc = self.spawner.processes[0]
        proc.timeout_on_wait = True
        self.manager.stop(timeout=0.01)
        self.assertTrue(proc.terminated)
        self.assertTrue(proc.killed)

    def test_stop_twice(self):
        self.manager.start()
        self.manager.stop()
        self.manager.stop()
        self.assertEqual(self.manager.state, MinerState.STOPPED)

    def test_shutdown_alias(self):
        self.manager.start()
        self.manager.shutdown()
        self.assertEqual(self.manager.state, MinerState.STOPPED)

    def test_normal_running_poll(self):
        self.manager.start()
        self.assertEqual(self.manager.reconcile(), MinerState.RUNNING)

    def test_first_crash_schedules_retry(self):
        self.manager.start()
        self.spawner.processes[0].crash()
        self.assertEqual(self.manager.reconcile(), MinerState.ERROR)
        self.assertEqual(self.manager.retry_count, 1)
        self.assertEqual(self.manager.retry_at, 1005.0)

    def test_retry_after_delay(self):
        self.manager.start()
        self.spawner.processes[0].crash()
        self.manager.reconcile()
        self.clock.advance(4)
        self.manager.reconcile()
        self.assertEqual(len(self.spawner.processes), 1)
        self.clock.advance(1)
        self.manager.reconcile()
        self.assertEqual(len(self.spawner.processes), 2)
        self.assertEqual(self.manager.state, MinerState.RUNNING)

    def test_retry_limit(self):
        self.manager.start()
        for delay in (5, 15, 30):
            self.spawner.processes[-1].crash()
            self.manager.reconcile()
            self.clock.advance(delay)
            self.manager.reconcile()
        self.spawner.processes[-1].crash()
        self.manager.reconcile()
        self.assertFalse(self.manager.desired_running)
        self.assertIsNone(self.manager.retry_at)
        self.assertEqual(self.manager.state, MinerState.ERROR)

    def test_manual_stop_cancels_retry(self):
        self.manager.start()
        self.spawner.processes[0].crash()
        self.manager.reconcile()
        self.manager.stop()
        self.clock.advance(100)
        self.manager.reconcile()
        self.assertEqual(len(self.spawner.processes), 1)

    def test_restart_counter_resets_after_stable_run(self):
        self.manager.start()
        self.spawner.processes[0].crash()
        self.manager.reconcile()
        self.clock.advance(5)
        self.manager.reconcile()
        self.clock.advance(300)
        self.manager.reconcile()
        self.assertEqual(self.manager.retry_count, 0)

    def test_last_exit_code(self):
        self.manager.start()
        self.spawner.processes[0].crash(23)
        self.manager.reconcile()
        self.assertEqual(self.manager.last_exit_code, 23)

    def test_spawn_failure_sanitizes_errors(self):
        self.spawner.fail = True
        self.assertFalse(self.manager.start())
        self.assertNotIn("SECRET_WALLET", str(self.manager.last_error))
        self.assertEqual(self.manager.retry_count, 1)

    def test_stop_does_not_spawn_without_start(self):
        self.manager.stop()
        self.assertEqual(len(self.spawner.processes), 0)

    def test_light_mode(self):
        (self.dir / "meminfo").write_text("MemAvailable: 2000000 kB\n", encoding="ascii")
        self.manager.start()
        self.assertIn("--randomx-mode=light", self.spawner.args[0][0])

    def test_cgroup_limit_overrides_host_memory(self):
        (self.dir / "max").write_text(str(2 * 1024**3), encoding="ascii")
        self.manager.start()
        self.assertIn("--randomx-mode=light", self.spawner.args[0][0])

    def test_explicit_no_tls(self):
        config = parse_config({
            "pool": "pool.supportxmr.com", "port": 443,
            "wallet": "SECRET_WALLET", "tls_mode": "disabled",
        })
        manager = MinerManager(config, binary="/fake/xmrig", memory_paths=self.paths,
                               clock=self.clock, popen=self.spawner)
        manager.start()
        self.assertNotIn("--tls", self.spawner.args[0][0])

    def test_reject_relative_executable(self):
        with self.assertRaises(ValueError):
            MinerManager(self.config, binary="xmrig")

    def test_reject_invalid_timeout(self):
        with self.assertRaises(ValueError):
            self.manager.stop(-1)

    def test_no_mqtt_dependency(self):
        import ast
        source = (APP_DIR / "miner_manager.py").read_text(encoding="utf-8")
        imports = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any("mqtt" in ast.dump(n).lower() for n in imports))


if __name__ == "__main__":
    unittest.main(verbosity=2)
