from __future__ import annotations

import argparse
import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doom_agent.cli.evaluate import add_evaluate_arguments
from doom_agent.cli.main import _build_parser, _print_scenarios
from doom_agent.cli.train import add_train_arguments


class CliTests(unittest.TestCase):
    def test_train_parser_uses_default_profile_implicitly(self) -> None:
        parser = add_train_arguments(io_arg_parser("train"))
        args = parser.parse_args(["--scenario", "deadly_corridor"])
        self.assertEqual(args.config, "default")
        self.assertEqual(args.scenario, "deadly_corridor")

    def test_evaluate_parser_uses_default_profile_implicitly(self) -> None:
        parser = add_evaluate_arguments(io_arg_parser("evaluate"))
        args = parser.parse_args(["--scenario", "health_gathering"])
        self.assertEqual(args.config, "default")
        self.assertEqual(args.scenario, "health_gathering")

    def test_list_scenarios_highlights_public_configuration(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            _print_scenarios()

        output = buffer.getvalue()
        self.assertIn("Configuracion publica:", output)
        self.assertIn("Escenarios para entrenamiento normal:", output)
        self.assertIn("- default: flujo normal por escenario", output)

    def test_list_profiles_remains_alias_of_list_scenarios(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["list-profiles"])
        self.assertEqual(args.command, "list-profiles")

    def test_list_scenarios_is_public_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["list-scenarios"])
        self.assertEqual(args.command, "list-scenarios")


def io_arg_parser(prog: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog=prog)
