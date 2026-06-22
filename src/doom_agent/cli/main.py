from __future__ import annotations

import argparse
import json

from doom_agent.cli.evaluate import add_evaluate_arguments
from doom_agent.cli.hydrate import add_hydrate_arguments
from doom_agent.cli.promote import add_promote_arguments
from doom_agent.cli.runs import add_inspect_run_arguments
from doom_agent.cli.sync import add_sync_arguments
from doom_agent.cli.train import add_train_arguments
from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.persistence.enums import SyncStatus
from doom_agent.persistence.repositories import TrainingRunRepository
from doom_agent.services.sync import ArtifactSyncService
from doom_agent.utils.checkpoints import list_all_checkpoints, resolve_checkpoint_preference
from doom_agent.utils.console import print_block, print_kv_block
from doom_agent.utils.reports import list_experiment_runs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "CLI unificada para Agente Doom. "
            "Modelo foundation con entrenamiento, evaluacion e inspeccion."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Entrena modelo foundation.")
    add_train_arguments(train_parser)

    evaluate_parser = subparsers.add_parser("evaluate", help="Evalua un checkpoint.")
    add_evaluate_arguments(evaluate_parser)

    list_checkpoints_parser = subparsers.add_parser(
        "list-checkpoints", help="Lista checkpoints conocidos."
    )
    list_checkpoints_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Cantidad maxima de checkpoints a mostrar.",
    )

    list_runs_parser = subparsers.add_parser(
        "list-runs", help="Lista reportes de entrenamiento registrados."
    )
    list_runs_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Cantidad maxima de corridas a mostrar.",
    )

    inspect_run_parser = subparsers.add_parser(
        "inspect-run",
        help="Muestra resumen consolidado de report + manifest para una corrida.",
    )
    add_inspect_run_arguments(inspect_run_parser)

    inspect_parser = subparsers.add_parser(
        "inspect-checkpoint", help="Muestra la metadata de un checkpoint."
    )
    add_evaluate_arguments(inspect_parser)

    promote_parser = subparsers.add_parser(
        "promote-checkpoint",
        help="Reevalua un checkpoint offline y lo promueve como alias oficial.",
    )
    add_promote_arguments(promote_parser)

    sync_parser = subparsers.add_parser(
        "sync-artifacts", help="Resincroniza artefactos locales hacia storage remoto."
    )
    add_sync_arguments(sync_parser)

    hydrate_parser = subparsers.add_parser(
        "hydrate-workspace",
        help="Reconstruye alias oficiales y soporte minimo desde storage remoto.",
    )
    add_hydrate_arguments(hydrate_parser)
    return parser


def _print_checkpoints(limit: int) -> None:
    checkpoints = list_all_checkpoints(build_project_paths())[:limit]
    if not checkpoints:
        print("No se encontraron checkpoints.")
        return

    for checkpoint in checkpoints:
        metadata = checkpoint.metadata
        training_status = "legacy" if metadata is None else metadata["training_status"]
        profile_name = "legacy" if metadata is None else metadata["profile_name"]
        checkpoint_role = None if metadata is None else metadata["checkpoint_role"]
        evaluation_source = None if metadata is None else metadata["evaluation_source"]
        mean_reward = None
        if metadata is not None and metadata["evaluation_metrics"] is not None:
            mean_reward = metadata["evaluation_metrics"]["mean_reward"]
        print(
            f"- {checkpoint.checkpoint_stem.with_suffix('.zip')}: "
            f"profile={profile_name}, timesteps={checkpoint.saved_timesteps}, "
            f"status={training_status}, role={checkpoint_role}, "
            f"eval_source={evaluation_source}, mean_reward={mean_reward}"
        )


def _print_runs(limit: int) -> None:
    from doom_agent.services.run_inspection import inspect_run

    runs = list_experiment_runs(build_project_paths())[:limit]
    if not runs:
        print("No se encontraron reportes de entrenamiento.")
        return

    for run in runs:
        try:
            inspection = inspect_run(run["run_id"])
            print(
                f"- {inspection['created_at_utc']}: run_id={inspection['run_id']}, "
                f"profile={inspection['profile_name']}, scenario={inspection['scenario_key']}, "
                f"timesteps={inspection['saved_timesteps']}, status={inspection['training_status']}, "
                f"sync={inspection['sync_status']}, mean_reward={inspection['mean_reward']}, "
                f"best={'yes' if inspection['best_checkpoint_archive_exists'] else 'no'}, "
                f"auto_selected={inspection['selected_auto_checkpoint_count']}, "
                f"manifest={'yes' if inspection['manifest_exists'] else 'no'}, "
                f"report={inspection['report_path']}"
            )
            continue
        except FileNotFoundError:
            pass
        print(
            f"- {run['created_at_utc']}: run_id={run['run_id']}, "
            f"profile={run['profile_name']}, scenario={run['scenario_key']}, "
            f"timesteps={run['saved_timesteps']}, status={run['training_status']}, "
            f"mean_reward={run['mean_reward']}, report={run['report_path']}"
        )


def _inspect_checkpoint(args: argparse.Namespace) -> None:
    project_paths = build_project_paths()
    checkpoint_name = args.checkpoint
    if checkpoint_name is None:
        checkpoint_name = get_training_profile(
            args.config,
            scenario_name=args.scenario,
        ).checkpoint_name

    checkpoint = resolve_checkpoint_preference(
        project_paths,
        checkpoint_name,
        preference=args.select,
    )
    print(f"Checkpoint resuelto: {checkpoint.checkpoint_stem.with_suffix('.zip')}")
    print(f"Timesteps guardados: {checkpoint.saved_timesteps}")
    if checkpoint.metadata is None:
        print("Checkpoint legacy sin metadata estructurada.")
        return

    print(json.dumps(checkpoint.metadata, indent=2, sort_keys=True))


def _inspect_run(args: argparse.Namespace) -> None:
    from doom_agent.services.run_inspection import inspect_run

    inspection = inspect_run(args.run_id)
    if args.json_output:
        print(json.dumps(inspection, indent=2, sort_keys=True))
        return

    print_kv_block(
        "Run Inspection",
        [
            ("run_id", inspection["run_id"]),
            ("created_at", inspection["created_at_utc"]),
            ("profile", inspection["profile_name"]),
            ("scenario", inspection["scenario_key"]),
            ("checkpoint", inspection["checkpoint_name"]),
            ("seed", inspection["seed"]),
            ("saved_timesteps", inspection["saved_timesteps"]),
            ("status", inspection["training_status"]),
            ("sync_status", inspection["sync_status"]),
            ("mean_reward", inspection["mean_reward"]),
            ("std_reward", inspection["std_reward"]),
            ("mean_episode_length", inspection["mean_episode_length"]),
            ("eval_episodes", inspection["evaluation_episodes"]),
            ("eval_history", inspection["evaluation_history_count"]),
            ("latest_eval_step", inspection["latest_evaluation_step"]),
            ("report", inspection["report_path"]),
            ("manifest", inspection["manifest_path"]),
            ("final_checkpoint", inspection["checkpoint_archive_path"]),
            ("best_checkpoint", inspection["best_checkpoint_archive_path"]),
            ("selected_auto", inspection["selected_auto_checkpoint_count"]),
            ("remote_candidates", inspection["remote_sync_candidate_count"]),
            ("handoff_ready", inspection["handoff_ready"]),
        ],
    )
    if inspection["selected_auto_checkpoint_archive_paths"]:
        print_block(
            "Selected Auto Checkpoints",
            inspection["selected_auto_checkpoint_archive_paths"],
        )
    if inspection["remote_sync_candidates"]:
        print_block(
            "Remote Sync Candidates",
            inspection["remote_sync_candidates"],
        )


def _print_sync_preview(args: argparse.Namespace) -> None:
    service = ArtifactSyncService()
    run_ids = _resolve_sync_run_ids(args)
    if not run_ids:
        print("No se encontraron corridas para sincronizar.")
        return

    for run_id in run_ids:
        preview = service.describe_run_sync(run_id)
        if not preview.candidates:
            print_block(
                "Artifact Sync Preview",
                [
                    f"run_id={run_id}",
                    "Sin candidatos de sync.",
                ],
            )
            continue

        print_kv_block(
            "Artifact Sync Preview",
            [
                ("run_id", preview.run_id),
                ("backend", preview.storage_backend),
                ("candidates", len(preview.candidates)),
            ],
        )
        for candidate in preview.candidates:
            print_kv_block(
                "Artifact",
                [
                    ("artifact_id", candidate.artifact_id),
                    ("type", candidate.artifact_type),
                    ("role", candidate.artifact_role),
                    ("local_path", candidate.local_path),
                    ("object_key", candidate.object_key),
                ],
            )


def _run_sync(args: argparse.Namespace) -> None:
    from doom_agent.services.workspace_handoff import publish_local_workspace_state

    if args.dry_run:
        _print_sync_preview(args)
        return

    service = ArtifactSyncService()
    run_ids = _resolve_sync_run_ids(args)
    if not run_ids:
        print("No se encontraron corridas para sincronizar.")
        return

    for result in service.sync_runs(run_ids):
        if result.attempted_count == 0:
            print_block(
                "Artifact Sync",
                [
                    f"run_id={result.run_id}",
                    "Sin candidatos de sync.",
                ],
            )
            continue
        print_kv_block(
            "Artifact Sync",
            [
                ("run_id", result.run_id),
                ("attempted", result.attempted_count),
                ("synced", result.synced_count),
                ("failed", result.failed_count),
                ("status", result.final_status),
            ],
        )

    try:
        publish_result = publish_local_workspace_state(root_dir=build_project_paths().root_dir)
    except Exception as error:
        print_block(
            "Workspace Handoff Warning",
            [
                "No se pudo publicar estado compartido despues del sync.",
                f"error={type(error).__name__}: {error}",
            ],
        )
        return

    if publish_result.uploaded:
        print_kv_block(
            "Workspace Handoff",
            [
                ("aliases", publish_result.alias_count),
                ("state", publish_result.state_path),
                ("object_key", publish_result.state_object_key),
            ],
        )


def _resolve_sync_run_ids(args: argparse.Namespace) -> list[str]:
    if args.run_id is not None:
        return [args.run_id]

    repository = TrainingRunRepository()
    sync_status = SyncStatus.LOCAL_ONLY.value if args.all_local_only else SyncStatus.FAILED.value
    return repository.list_run_ids_by_sync_status(sync_status=sync_status, limit=args.limit)


def _run_hydrate(args: argparse.Namespace) -> None:
    from doom_agent.services.workspace_handoff import hydrate_workspace

    include_active = args.only in {"active", "both"}
    include_promoted = args.only in {"promoted", "both"}
    result = hydrate_workspace(
        profile_name=args.config,
        scenario_name=args.scenario,
        include_active=include_active,
        include_promoted=include_promoted,
    )
    print_kv_block(
        "Workspace Hydration",
        [
            ("checkpoint", result.checkpoint_name),
            ("state", result.state_path),
            ("pointers", len(result.hydrated_pointers)),
        ],
    )
    for pointer in result.hydrated_pointers:
        print_kv_block(
            "Hydrated Pointer",
            [
                ("kind", pointer.pointer_kind),
                ("run_id", pointer.run_id),
                ("alias", pointer.local_alias_path),
                ("run_checkpoint", pointer.restored_run_checkpoint_path),
                ("report", pointer.restored_report_path),
            ],
        )


def main() -> None:
    from doom_agent.services.evaluator import evaluate
    from doom_agent.services.promoter import promote_checkpoint
    from doom_agent.services.trainer import train

    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "train":
        if args.from_scratch and args.resume not in {"auto", "latest"}:
            raise SystemExit(
                "No puedes usar '--from-scratch' junto con un checkpoint explicito en '--resume'."
            )
        train(
            profile_name=args.config,
            requested_timesteps=args.timesteps,
            scenario_name=args.scenario,
            seed=args.seed,
            n_steps=args.n_steps,
            num_envs=args.num_envs,
            resume_mode=args.resume,
            from_scratch=args.from_scratch,
            eval_frequency=args.eval_freq,
            eval_episodes=args.eval_episodes,
            save_best=not args.no_save_best,
            allow_scenario_resume=args.allow_scenario_resume,
        )
        return

    if args.command == "evaluate":
        evaluate(
            checkpoint_name=args.checkpoint,
            steps=args.steps,
            episodes=args.episodes,
            profile_name=args.config,
            checkpoint_selection=args.select,
            scenario_name=args.scenario,
            render=not args.no_render,
            json_output=args.json_output,
        )
        return

    if args.command == "list-checkpoints":
        _print_checkpoints(args.limit)
        return

    if args.command == "list-runs":
        _print_runs(args.limit)
        return

    if args.command == "inspect-run":
        _inspect_run(args)
        return

    if args.command == "inspect-checkpoint":
        _inspect_checkpoint(args)
        return

    if args.command == "promote-checkpoint":
        result = promote_checkpoint(
            checkpoint_name=args.checkpoint,
            episodes=args.episodes,
            profile_name=args.config,
            checkpoint_selection=args.select,
            scenario_name=args.scenario,
        )
        metrics = result.summary["metrics"]
        print_kv_block(
            "Checkpoint Promotion",
            [
                ("source", str(result.source_checkpoint_path)),
                ("promoted", str(result.promoted_checkpoint_path)),
                ("episodes", metrics["episodes"]),
                ("mean_reward", metrics["mean_reward"]),
                ("std_reward", metrics["std_reward"]),
                ("mean_episode_length", metrics["mean_episode_length"]),
            ],
        )
        return

    if args.command == "sync-artifacts":
        _run_sync(args)
        return

    if args.command == "hydrate-workspace":
        _run_hydrate(args)
        return

    raise SystemExit(f"Comando no soportado: {args.command}")


if __name__ == "__main__":
    main()
