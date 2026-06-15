from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.cli.evaluate import add_evaluate_arguments
from doom_agent.cli.main import _build_parser
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

    def test_removed_commands_stay_removed_from_public_parser(self) -> None:
        parser = _build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["sweep", "--scenario", "basic"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["list-scenarios"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["list-profiles"])


def io_arg_parser(prog: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog=prog)
