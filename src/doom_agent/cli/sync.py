from __future__ import annotations

import argparse


def add_sync_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--run-id",
        default=None,
        help="Sincroniza una corrida especifica por run_id.",
    )
    target_group.add_argument(
        "--all-local-only",
        action="store_true",
        help="Sincroniza corridas con estado local_only.",
    )
    target_group.add_argument(
        "--all-failed",
        action="store_true",
        help="Reintenta corridas con estado failed.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Cantidad maxima de corridas a procesar en modo batch.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra candidatos de sync sin subir nada ni cambiar DB.",
    )
    return parser
