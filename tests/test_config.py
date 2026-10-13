

"""Isolated unit tests for the HAOS Python configuration module."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "xmrig_haos"
    / "rootfs"
    / "app"
    / "config.py"
)

spec = importlib.util.spec_from_file_location(
    "xmrig_haos_config",
    MODULE_PATH,
)

assert spec is not None and spec.loader is not None

import sys

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

ConfigError = module.ConfigError
load_config = module.load_config
parse_config = module.parse_config


class ConfigurationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.valid = {
            "pool": "pool.supportxmr.com",
            "port": 443,
            "wallet": "TEST_WALLET_SECRET",
            "worker": "HA",
            "threads": 2,
            "priority": 2,
            "tls_mode": "auto",
        }

    def test_all_existing_options(self):
        config = parse_config(self.valid)

        self.assertEqual(
            (
                config.pool_url,
                config.wallet,
                config.worker,
            ),
            (
                "pool.supportxmr.com:443",
                "TEST_WALLET_SECRET",
                "HA",
            ),
        )

        self.assertEqual(
            (
                config.threads,
                config.priority,
                config.tls_mode,
            ),
            (2, 2, "auto"),
        )

    def test_default_tls_when_missing(self):
        self.valid.pop("tls_mode")

        self.assertEqual(
            parse_config(self.valid).tls_mode,
            "auto",
        )

    def test_default_optional_options(self):
        config = parse_config({
            "wallet": "TEST_WALLET_SECRET",
        })

        self.assertEqual(
            (
                config.pool,
                config.port,
                config.worker,
                config.threads,
                config.priority,
                config.tls_mode,
            ),
            (
                "pool.supportxmr.com",
                443,
                "HA",
                2,
                2,
                "auto",
            ),
        )

    def test_missing_wallet_is_rejected(self):
        self.valid["wallet"] = ""

        with self.assertRaises(ConfigError):
            parse_config(self.valid)

    def test_invalid_json_root(self):
        with self.assertRaises(ConfigError):
            parse_config([])

    def test_invalid_port_limits(self):
        for invalid in (
            0,
            65536,
            -1,
            "wrong",
            True,
            1.5,
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ConfigError):
                    parse_config({
                        **self.valid,
                        "port": invalid,
                    })

    def test_invalid_threads_limits(self):
        for invalid in (
            0,
            257,
            -1,
            False,
            2.3,
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ConfigError):
                    parse_config({
                        **self.valid,
                        "threads": invalid,
                    })

    def test_invalid_priority_limits(self):
        for invalid in (
            -1,
            6,
            True,
            "high",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ConfigError):
                    parse_config({
                        **self.valid,
                        "priority": invalid,
                    })

    def test_numeric_strings(self):
        config = parse_config({
            **self.valid,
            "port": "00443",
            "threads": "04",
            "priority": "00",
        })

        self.assertEqual(
            (
                config.port,
                config.threads,
                config.priority,
            ),
            (443, 4, 0),
        )

    def test_tls_auto(self):
        self.assertTrue(
            parse_config(self.valid).tls_enabled
        )

        self.assertFalse(
            parse_config({
                **self.valid,
                "port": 3333,
            }).tls_enabled
        )

    def test_tls_enabled_any_port(self):
        self.assertTrue(
            parse_config({
                **self.valid,
                "port": 3333,
                "tls_mode": "enabled",
            }).tls_enabled
        )

    def test_tls_disabled_any_port(self):
        self.assertFalse(
            parse_config({
                **self.valid,
                "tls_mode": "disabled",
            }).tls_enabled
        )

    def test_invalid_tls_mode(self):
        with self.assertRaises(ConfigError):
            parse_config({
                **self.valid,
                "tls_mode": "invalid",
            })

    def test_hostname_with_embedded_port(self):
        config = parse_config({
            **self.valid,
            "pool": "stratum+tcp://pool.example.org:3333",
        })

        self.assertEqual(
            config.pool_url,
            "pool.example.org:443",
        )

    def test_bracketed_ipv6(self):
        config = parse_config({
            **self.valid,
            "pool": "[2001:db8::1]:3333",
        })

        self.assertEqual(
            config.pool_url,
            "[2001:db8::1]:443",
        )

    def test_invalid_pool_addresses(self):
        for invalid in (
            "",
            "pool.example.org/path",
            "pool.example.org@evil",
            "pool example.org",
            "2001:db8::1",
            "[not-ipv6]",
            "pool.example.org:abc",
        ):
            with self.subTest(pool=invalid):
                with self.assertRaises(ConfigError):
                    parse_config({
                        **self.valid,
                        "pool": invalid,
                    })

    def test_reject_control_characters(self):
        with self.assertRaises(ConfigError):
            parse_config({
                **self.valid,
                "worker": "HA\nFake",
            })

    def test_wallet_not_exposed_in_repr(self):
        self.assertNotIn(
            "TEST_WALLET_SECRET",
            repr(parse_config(self.valid)),
        )

    def test_invalid_config_error_does_not_expose_wallet(self):
        with self.assertRaises(ConfigError) as caught:
            parse_config({
                **self.valid,
                "threads": 0,
            })

        self.assertNotIn(
            "TEST_WALLET_SECRET",
            str(caught.exception),
        )

    def test_additional_keys_are_ignored_for_forward_compatibility(self):
        self.assertEqual(
            parse_config({
                **self.valid,
                "future_option": "value",
            }).port,
            443,
        )

    def test_load_options_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "options.json"

            path.write_text(
                json.dumps(self.valid),
                encoding="utf-8",
            )

            self.assertEqual(
                load_config(path).worker,
                "HA",
            )

    def test_corrupt_options_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "options.json"

            path.write_text(
                "{invalid",
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(path)

    def test_missing_options_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ConfigError):
                load_config(
                    Path(directory) / "missing.json"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
