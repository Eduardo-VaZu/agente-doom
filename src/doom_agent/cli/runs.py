from __future__ import annotations

import argparse


def add_inspect_run_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--run-id",
        required=True,
        help="Identificador exacto de corrida a inspeccionar.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Imprime resumen estructurado en JSON.",
    )
    return parser
