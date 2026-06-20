from __future__ import annotations

import argparse

from doom_agent.config import DEFAULT_PROFILE_NAME, PROFILE_NAMES, SCENARIO_NAMES

AUTO_RESUME_MODE = "auto"
LATEST_RESUME_MODE = "latest"


def add_train_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--config",
        choices=PROFILE_NAMES,
        default=DEFAULT_PROFILE_NAME,
        help="Configuracion base del modelo foundation.",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=None,
        help="Sobrescribe los timesteps solicitados para esta ejecucion.",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIO_NAMES,
        default=None,
        help="Escenario de entrenamiento actual. Hoy el flujo activo usa 'basic'.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Sobrescribe la seed base para esta ejecucion.",
    )
    parser.add_argument(
        "--resume",
        default=AUTO_RESUME_MODE,
        help=(
            "Checkpoint desde el cual reanudar. Usa 'auto' para buscar el ultimo "
            "compatible, 'latest' para forzarlo o una ruta/nombre de checkpoint."
        ),
    )
    parser.add_argument(
        "--from-scratch",
        action="store_true",
        help="Ignora checkpoints previos y comienza desde cero.",
    )
    parser.add_argument(
        "--allow-scenario-resume",
        action="store_true",
        help=(
            "Permite usar un checkpoint de otro escenario cuando la arquitectura "
            "del modelo es compatible."
        ),
    )
    parser.add_argument(
        "--eval-freq",
        type=int,
        default=None,
        help="Frecuencia de evaluacion periodica en pasos. Por defecto usa valor del perfil.",
    )
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=None,
        help="Cantidad de episodios por evaluacion periodica. Por defecto usa valor del perfil.",
    )
    parser.add_argument(
        "--no-save-best",
        action="store_true",
        help="No guardar el mejor modelo segun evaluacion periodica.",
    )
    return parser


def parse_args() -> argparse.Namespace:
    parser = add_train_arguments(
        argparse.ArgumentParser(
            description=(
                "Entrena modelo foundation. "
                "Etapa activa actual: escenario basic."
            )
        )
    )
    return parser.parse_args()


def main() -> None:
    from doom_agent.services.trainer import train

    args = parse_args()
    if args.from_scratch and args.resume not in {AUTO_RESUME_MODE, LATEST_RESUME_MODE}:
        raise SystemExit(
            "No puedes usar '--from-scratch' junto con un checkpoint explicito en '--resume'."
        )

    train(
        profile_name=args.config,
        requested_timesteps=args.timesteps,
        scenario_name=args.scenario,
        seed=args.seed,
        resume_mode=args.resume,
        from_scratch=args.from_scratch,
        eval_frequency=args.eval_freq,
        eval_episodes=args.eval_episodes,
        save_best=not args.no_save_best,
        allow_scenario_resume=args.allow_scenario_resume,
    )


if __name__ == "__main__":
    main()
