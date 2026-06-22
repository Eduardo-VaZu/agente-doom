from __future__ import annotations

import argparse

from doom_agent.config import DEFAULT_PROFILE_NAME


def add_hydrate_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--config",
        default=DEFAULT_PROFILE_NAME,
        help="Perfil base del checkpoint a hidratar. Default: default.",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Escenario a usar para resolver nombre de checkpoint del perfil.",
    )
    parser.add_argument(
        "--only",
        choices=("active", "promoted", "both"),
        default="both",
        help="Define si hidratar alias active, promoted o ambos.",
    )
    return parser
