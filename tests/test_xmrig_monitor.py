"""Offline tests for the XMRig read-only loopback monitor."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "xmrig_haos" / "rootfs" / "app" / "xmrig_monitor.py"
)
spec = importlib.util.spec_from_file_location("xmrig_monitor_tested", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
Monitor = module.XmrigMonitor
parse_summary = module.parse_summary

SAMPLE = {
    "uptime": 121,
    "hashrate": {"total": [2350.2, 2300.3, None]},
    "connection": {"uptime": 120, "accepted": 8, "rejected": 1},
    "results": {"shares_good": 8, "shares_total": 9},
}


class ParserTests(unittest.TestCase):
    def test_complete(self):
        snapshot = parse_summary(SAMPLE)
        self.assertTrue(snapshot.api_available)
        self.assertEqual(snapshot.hashrate_10s, 2350.2)
        self.assertEqual(snapshot.hashrate_60s, 2300.3)
        self.assertIsNone(snapshot.hashrate_15m)
        self.assertEqual((snapshot.accepted, snapshot.rejected), (8, 1))
        self.assertEqual(snapshot.uptime_seconds, 121)
        self.assertTrue(snapshot.pool_connected)

    def test_empty_object_is_not_zero(self):
        snapshot = parse_summary({})
        self.assertTrue(snapshot.api_available)
        self.assertIsNone(snapshot.hashrate_10s)
        self.assertIsNone(snapshot.accepted)
        self.assertIsNone(snapshot.pool_connected)

    def test_invalid_root(self):
        self.assertEqual(parse_summary([]).error, "invalid_payload")

    def test_reject_negative_hashrate(self):
        self.assertIsNone(parse_summary({"hashrate": {"total": [-1]}}).hashrate_10s)

    def test_reject_nan_hashrate(self):
        self.assertIsNone(parse_summary({"hashrate": {"total": [float("nan")]}}).hashrate_10s)

    def test_reject_boolean_values(self):
        snap = parse_summary({"uptime": True, "hashrate": {"total": [True]}})
        self.assertIsNone(snap.uptime_seconds)
        self.assertIsNone(snap.hashrate_10s)

    def test_bad_hashrate_shape(self):
        self.assertIsNone(parse_summary({"hashrate": {"total": "5"}}).hashrate_10s)

    def test_share_fallback(self):
        snap = parse_summary({"results": {"shares_good": 4, "shares_total": 7}})
        self.assertEqual((snap.accepted, snap.rejected), (4, 3))

    def test_share_fallback_no_underflow(self):
        snap = parse_summary({"results": {"shares_good": 7, "shares_total": 4}})
        self.assertIsNone(snap.rejected)

    def test_explicit_disconnected(self):
        self.assertFalse(parse_summary({"connection": {"connected": False, "uptime": 10}}).pool_connected)

    def test_zero_connection_uptime_is_unknown(self):
        self.assertIsNone(parse_summary({"connection": {"uptime": 0}}).pool_connected)

    def test_unexpected_nested_data(self):
        self.assertTrue(parse_summary({"hashrate": 3, "results": [], "connection": "x"}).api_available)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.status = 200
        cls.body = json.dumps(SAMPLE).encode("utf-8")
        cls.received_path = None
        cls.received_auth = None

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                cls.received_path = self.path
                cls.received_auth = self.headers.get("Authorization")
                self.send_response(cls.status)
                if cls.status == 302:
                    self.send_header("Location", "http://example.invalid/secret")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                try:
                    self.wfile.write(cls.body)
                except BrokenPipeError:
                    pass

            def log_message(self, *_args):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        type(self).status = 200
        type(self).body = json.dumps(SAMPLE).encode("utf-8")
        type(self).received_path = None
        type(self).received_auth = None

    def test_reads_summary(self):
        snap = Monitor(port=self.port).poll()
        self.assertTrue(snap.api_available)
        self.assertEqual(self.received_path, "/2/summary")

    def test_sends_optional_authorization(self):
        self.assertTrue(Monitor(port=self.port, access_token="test-token").poll().api_available)
        self.assertEqual(self.received_auth, "Bearer test-token")

    def test_without_token(self):
        Monitor(port=self.port).poll()
        self.assertIsNone(self.received_auth)

    def test_http_error(self):
        type(self).status = 503
        self.assertFalse(Monitor(port=self.port).poll().api_available)

    def test_no_redirect(self):
        type(self).status = 302
        self.assertFalse(Monitor(port=self.port, access_token="test-token").poll().api_available)

    def test_invalid_json(self):
        type(self).body = b"{bad-json"
        self.assertEqual(Monitor(port=self.port).poll().error, "invalid_json")

    def test_invalid_utf8(self):
        type(self).body = b"\xff\xfe"
        self.assertEqual(Monitor(port=self.port).poll().error, "invalid_json")

    def test_root_not_object(self):
        type(self).body = b"[]"
        self.assertEqual(Monitor(port=self.port).poll().error, "invalid_payload")

    def test_response_size_limit(self):
        type(self).body = b" " * (module.MAX_RESPONSE_BYTES + 1)
        self.assertEqual(Monitor(port=self.port).poll().error, "response_too_large")

    def test_connection_refused(self):
        probe = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        unused_port = probe.server_address[1]
        probe.server_close()
        self.assertFalse(Monitor(port=unused_port, timeout=0.2).poll().api_available)

    def test_invalid_port(self):
        for port in (0, 65536, True, "18080"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                Monitor(port=port)

    def test_invalid_timeout(self):
        for timeout in (0, -1, float("nan"), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                Monitor(port=self.port, timeout=timeout)

    def test_invalid_token(self):
        for token in ("", "bad\nheader", "bad token"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                Monitor(port=self.port, access_token=token)


if __name__ == "__main__":
    unittest.main(verbosity=2)
