"""Tests for the beta-only /proc + cgroup telemetry; no privileges or mining."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xmrig_haos_beta.rootfs.app.resource_monitor import ResourceMonitor, ResourceSnapshot
from xmrig_haos_beta.rootfs.app.mqtt_discovery import DiscoveryPayloads


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.proc = self.root / "proc"
        self.cg = self.root / "cgroup"
        (self.proc / "123").mkdir(parents=True)
        (self.proc / "net").mkdir()
        self.cg.mkdir()
        self.clock = 100.0
        self.monitor = ResourceMonitor(proc=self.proc, cgroup=self.cg, clock=lambda: self.clock)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        (self.root / name).write_text(value, encoding="ascii")

    def test_missing_sources_are_unknown_not_zero(self):
        value = self.monitor.poll(None)
        self.assertIsNone(value.container_cpu_percent)
        self.assertIsNone(value.container_ram_mib)
        self.assertIsNone(value.process_ram_mib)

    def test_cgroup_memory_cpu_network_and_disk(self):
        self.write("cgroup/cpu.stat", "usage_usec 1000000\n")
        self.write("cgroup/memory.current", "20971520\n")
        self.write("cgroup/memory.max", "104857600\n")
        self.write("cgroup/io.stat", "8:0 rbytes=1048576 wbytes=2097152 rios=1 wios=2\n")
        self.write("proc/net/dev",
                   "Inter-| Receive | Transmit\n face|bytes | bytes\n"
                   " lo: 1 0 0 0 0 0 0 0 2 0 0 0 0 0 0 0\n"
                   "eth0: 1048576 0 0 0 0 0 0 0 2097152 0 0 0 0 0 0 0\n")
        first = self.monitor.poll(None)
        self.assertEqual(first.container_ram_mib, 20.0)
        self.assertEqual(first.container_ram_percent, 20.0)
        self.assertEqual(first.container_net_rx_mib, 1.0)
        self.assertEqual(first.container_net_tx_mib, 2.0)
        self.assertEqual(first.container_disk_read_mib, 1.0)
        self.assertEqual(first.container_disk_write_mib, 2.0)
        self.assertIsNone(first.container_cpu_percent)
        self.clock += 5.0
        self.write("cgroup/cpu.stat", "usage_usec 11000000\n")
        self.assertEqual(self.monitor.poll(None).container_cpu_percent, 200.0)

    def test_process_pid_change_resets_cpu_baseline(self):
        # PID 123, comm with parentheses, 20 tokens after the comm field.
        bits = ["S"] + ["0"] * 49
        bits[11], bits[12], bits[19] = "100", "100", "77"
        self.write("proc/123/stat", "123 (xmrig (worker)) " + " ".join(bits) + "\n")
        self.write("proc/123/status", "VmRSS:\t2048 kB\nVmHWM:\t4096 kB\nThreads:\t3\n")
        first = self.monitor.poll(123)
        self.assertEqual(first.process_ram_mib, 2.0)
        self.assertEqual(first.process_ram_peak_mib, 4.0)
        self.assertEqual(first.process_threads, 3)
        self.assertIsNone(first.process_cpu_percent)
        self.clock += 1
        bits[11] = "300"
        self.write("proc/123/stat", "123 (xmrig (worker)) " + " ".join(bits) + "\n")
        later = self.monitor.poll(123)
        self.assertGreater(later.process_cpu_percent, 0)
        self.assertIsNone(self.monitor.poll(None).process_cpu_percent)
        self.assertIsNone(self.monitor.poll(123).process_cpu_percent)

    def test_mqtt_discovery_scopes(self):
        builder = DiscoveryPayloads()
        msgs = builder.discovery_messages()
        by_id = {json.loads(m.payload)["unique_id"]: json.loads(m.payload) for m in msgs}
        self.assertEqual(len(msgs), 21)
        self.assertEqual(by_id["xmrig_haos_beta_process_cpu_percent"]["availability_topic"],
                         builder.process_availability_topic)
        self.assertEqual(by_id["xmrig_haos_beta_container_cpu_percent"]["availability_topic"],
                         builder.mqtt_availability_topic)
        resource = builder.resource_messages(ResourceSnapshot(container_ram_mib=20.0))[0]
        self.assertFalse(resource.retain)
        data = json.loads(resource.payload)
        self.assertEqual(data["container_ram_mib"], 20.0)
        self.assertIsNone(data["process_cpu_percent"])


if __name__ == "__main__":
    unittest.main()
