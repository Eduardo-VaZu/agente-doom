from __future__ import annotations

import argparse

from doom_agent.config import DEFAULT_PROFILE_NAME, PROFILE_NAMES, SCENARIO_NAMES


def add_evaluate_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Nombre del checkpoint sin extension .zip, o ruta al archivo.",
    )
    parser.add_argument(
        "--config",
        choices=PROFILE_NAMES,
        default=DEFAULT_PROFILE_NAME,
        help=(
            "Configuracion base para derivar el checkpoint cuando no se pasa '--checkpoint'. "
            "Normalmente basta con usar '--scenario'."
        ),
    )
    parser.add_argument(
        "--select",
        choices=("best", "last", "exact"),
        default="best",
        help="Politica para resolver el checkpoint: mejor modelo, ultimo estado o nombre exacto.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Cantidad maxima de pasos de evaluacion.",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIO_NAMES,
        default=None,
        help="Sobrescribe el escenario de evaluacion. Util para checkpoints legacy o pruebas cruzadas.",
    )
    return parser


def parse_args() -> argparse.Namespace:
    parser = add_evaluate_arguments(
        argparse.ArgumentParser(
            description=(
                "Evalua checkpoints por escenario. "
                "Usa '--scenario' para resolver el checkpoint de 'default' si no indicas otro."
            )
        )
    )
    return parser.parse_args()


def main() -> None:
    from doom_agent.services.evaluator import evaluate

    args = parse_args()
    evaluate(
        checkpoint_name=args.checkpoint,
        steps=args.steps,
        profile_name=args.config,
        checkpoint_selection=args.select,
        scenario_name=args.scenario,
    )


if __name__ == "__main__":
    main()
