from __future__ import annotations

import argparse

from doom_agent.config import DEFAULT_PROFILE_NAME, PROFILE_NAMES, SCENARIO_NAMES


def add_promote_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Nombre del checkpoint sin extension .zip, o ruta al archivo a promover.",
    )
    parser.add_argument(
        "--config",
        choices=PROFILE_NAMES,
        default=DEFAULT_PROFILE_NAME,
        help="Configuracion base para definir alias oficial de promocion.",
    )
    parser.add_argument(
        "--select",
        choices=("best", "last", "exact"),
        default="exact",
        help="Politica para resolver checkpoint origen. Recomendado: usar ruta exacta.",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=50,
        help="Cantidad de episodios para reevaluacion offline antes de promover.",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIO_NAMES,
        default=None,
        help="Sobrescribe escenario al resolver perfil y alias oficial.",
    )
    return parser
