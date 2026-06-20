from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.cli.evaluate import add_evaluate_arguments
from doom_agent.cli.main import _build_parser
from doom_agent.cli.sync import add_sync_arguments
from doom_agent.cli.train import add_train_arguments


class CliTests(unittest.TestCase):
    def test_train_parser_uses_default_profile_implicitly(self) -> None:
        parser = add_train_arguments(io_arg_parser("train"))
        args = parser.parse_args(["--scenario", "basic"])
        self.assertEqual(args.config, "default")
        self.assertEqual(args.scenario, "basic")

    def test_evaluate_parser_uses_default_profile_implicitly(self) -> None:
        parser = add_evaluate_arguments(io_arg_parser("evaluate"))
        args = parser.parse_args(["--scenario", "basic"])
        self.assertEqual(args.config, "default")
        self.assertEqual(args.scenario, "basic")
        self.assertIsNone(args.episodes)
        self.assertFalse(args.no_render)
        self.assertFalse(args.json_output)

    def test_evaluate_parser_accepts_offline_summary_options(self) -> None:
        parser = add_evaluate_arguments(io_arg_parser("evaluate"))
        args = parser.parse_args(["--scenario", "basic", "--episodes", "20", "--no-render", "--json"])
        self.assertEqual(args.episodes, 20)
        self.assertTrue(args.no_render)
        self.assertTrue(args.json_output)

    def test_parser_keeps_train_and_evaluate_commands(self) -> None:
        parser = _build_parser()
        train_args = parser.parse_args(["train", "--scenario", "basic"])
        args = parser.parse_args(["evaluate", "--scenario", "basic"])
        self.assertEqual(train_args.command, "train")
        self.assertEqual(args.command, "evaluate")

    def test_parser_keeps_checkpoint_listing_commands(self) -> None:
        parser = _build_parser()
        self.assertEqual(parser.parse_args(["list-checkpoints"]).command, "list-checkpoints")
        self.assertEqual(parser.parse_args(["list-runs"]).command, "list-runs")
        self.assertEqual(
            parser.parse_args(["inspect-checkpoint", "--scenario", "basic"]).command,
            "inspect-checkpoint",
        )
        self.assertEqual(
            parser.parse_args(["sync-artifacts", "--run-id", "run-123"]).command,
            "sync-artifacts",
        )

    def test_removed_commands_stay_removed_from_public_parser(self) -> None:
        parser = _build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["sweep", "--scenario", "basic"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["list-scenarios"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["list-profiles"])

    def test_sync_parser_accepts_batch_modes(self) -> None:
        parser = add_sync_arguments(io_arg_parser("sync-artifacts"))
        args = parser.parse_args(["--all-local-only", "--limit", "5"])
        self.assertTrue(args.all_local_only)
        self.assertEqual(args.limit, 5)

        args = parser.parse_args(["--all-failed"])
        self.assertTrue(args.all_failed)

    def test_sync_parser_rejects_missing_or_multiple_targets(self) -> None:
        parser = add_sync_arguments(io_arg_parser("sync-artifacts"))
        with self.assertRaises(SystemExit):
            parser.parse_args([])
        with self.assertRaises(SystemExit):
            parser.parse_args(["--run-id", "run-1", "--all-failed"])


def io_arg_parser(prog: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog=prog)
