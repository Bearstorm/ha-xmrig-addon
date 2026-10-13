"""Persistent state file tests, isolated to temporary directories."""
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

P = Path(__file__).resolve().parents[1] / "xmrig_haos/rootfs/app/mining_state.py"
spec = importlib.util.spec_from_file_location("mining_state_test", P)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "xmrig_state.json"
        self.store = module.MiningStateStore(self.path)

    def test_missing_file_defaults_on(self):
        self.assertTrue(self.store.load())

    def test_save_off_and_reload(self):
        self.store.save(False)
        self.assertFalse(module.MiningStateStore(self.path).load())

    def test_save_on_and_reload(self):
        self.store.save(False)
        self.store.save(True)
        self.assertTrue(module.MiningStateStore(self.path).load())

    def test_file_permissions_private(self):
        self.store.save(False)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_reject_malformed_json(self):
        self.path.write_text("corrupted JSON")
        with self.assertRaises(module.StateStoreError):
            self.store.load()

    def test_reject_wrong_json_types(self):
        for value in ('{"version":1,"running":"false"}',
                      '{"version":1,"running":1}',
                      '{"version":2,"running":true}',
                      "null", "[]"):
            with self.subTest(value=value):
                self.path.write_text(value)
                with self.assertRaises(module.StateStoreError):
                    self.store.load()

    def test_reject_overlarge_file(self):
        self.path.write_bytes(b"x" * 257)
        with self.assertRaises(module.StateStoreError):
            self.store.load()

    def test_reject_invalid_save(self):
        with self.assertRaises(module.StateStoreError):
            self.store.save("OFF")

    def test_atomic_replace_failure_preserves_previous_state(self):
        self.store.save(False)
        with patch.object(module.os, "replace", side_effect=OSError("denied")):
            with self.assertRaises(module.StateStoreError):
                self.store.save(True)
        self.assertFalse(self.store.load())
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["xmrig_state.json"])

    def test_missing_parent_cannot_be_created(self):
        store = module.MiningStateStore(self.path.parent / "missing" / "state.json")
        with self.assertRaises(module.StateStoreError):
            store.save(False)


if __name__ == "__main__":
    unittest.main()
