from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from doom_agent.config import (
    build_project_paths,
    get_training_profile,
    materialize_curriculum_profiles,
)
from doom_agent.config.schema import TrainingProfile
from doom_agent.persistence import has_explicit_database_url
from doom_agent.persistence.repositories import TrainingRunRepository
from doom_agent.services.resume import AUTO_RESUME_MODE
from doom_agent.shared.contracts import TrainingRunReportPayload
from doom_agent.storage import build_run_artifact_paths, has_explicit_remote_storage_config
from doom_agent.utils.checkpoints import (
    best_checkpoint_stem,
    build_checkpoint_metadata,
    checkpoint_zip_path,
    copy_checkpoint_bundle,
    save_checkpoint_bundle,
)
from doom_agent.utils.console import print_block, print_kv_block
from doom_agent.utils.filesystem import ensure_directories
from doom_agent.utils.formatting import format_path_tail
from doom_agent.utils.reports import (
    build_run_id,
    build_training_run_report,
    save_training_run_report,
)

if TYPE_CHECKING:
    from doom_agent.services.resume import ResumeState
    from doom_agent.services.training_support import EvaluationSettings


def _resolve_vizdoom_exit_exception() -> type[Exception]:
    try:
        from vizdoom import ViZDoomUnexpectedExitException as resolved_exception
    except ModuleNotFoundError:  # pragma: no cover - only used in lightweight test environments
        class FallbackViZDoomUnexpectedExitException(Exception):
            pass

        return FallbackViZDoomUnexpectedExitException

    return resolved_exception


ViZDoomUnexpectedExitException = _resolve_vizdoom_exit_exception()


def _persist_run_report_to_database(
    report: TrainingRunReportPayload,
    report_path: Path,
) -> None:
    if not has_explicit_database_url():
        return

    try:
        TrainingRunRepository().upsert_run_report(report, report_path=report_path)
    except Exception as error:
        print_block(
            "Persistence Warning",
            [
                "No se pudo guardar metadata en PostgreSQL.",
                f"error={type(error).__name__}: {error}",
                "Reporte local sigue disponible.",
            ],
        )


def _sync_run_artifacts_to_remote(run_id: str) -> None:
    if not has_explicit_remote_storage_config():
        return

    from doom_agent.services.sync import ArtifactSyncService

    try:
        result = ArtifactSyncService().sync_run(run_id)
    except Exception as error:
        print_block(
            "Sync Warning",
            [
                "No se pudo sincronizar artefactos con MinIO.",
                f"error={type(error).__name__}: {error}",
                "Artefactos locales siguen disponibles.",
            ],
        )
        return

    if result.attempted_count == 0:
        return
    print_kv_block(
        "Artifact Sync",
        [
            ("run_id", run_id),
            ("attempted", result.attempted_count),
            ("synced", result.synced_count),
            ("failed", result.failed_count),
            ("status", result.final_status),
        ],
    )


def copy_run_best_checkpoint_if_updated(
    final_checkpoint_stem: Path,
    run_best_checkpoint_stem: Path,
    *,
    best_checkpoint_updated: bool,
) -> Path | None:
    if not best_checkpoint_updated:
        return None

    current_best_checkpoint_stem = best_checkpoint_stem(final_checkpoint_stem)
    current_best_checkpoint_path = checkpoint_zip_path(current_best_checkpoint_stem)
    if not current_best_checkpoint_path.exists():
        return None

    copy_checkpoint_bundle(current_best_checkpoint_stem, run_best_checkpoint_stem)
    return current_best_checkpoint_path


@dataclass(frozen=True, slots=True)
class TrainingExecutionResult:
    profile_name: str
    profile: TrainingProfile
    final_checkpoint_path: Path
    report_path: Path
    training_status: str
    completed: bool
    saved_timesteps: int
    stopped_early: bool
    stop_reason: str | None


def select_resume_checkpoint_path(result: TrainingExecutionResult) -> Path:
    final_checkpoint_stem = result.final_checkpoint_path.with_suffix("")
    best_checkpoint_path = checkpoint_zip_path(best_checkpoint_stem(final_checkpoint_stem))
    if best_checkpoint_path.exists():
        return best_checkpoint_path
    return result.final_checkpoint_path


def print_training_summary(
    profile_name: str,
    profile: TrainingProfile,
    checkpoints_dir: Path,
    resume_state: ResumeState,
    evaluation_settings: EvaluationSettings,
    run_label: str | None = None,
) -> None:
    title = f"Training Start | {profile_name}"
    if run_label:
        title = f"{title} | {run_label}"
    print_kv_block(
        title,
        [
            ("scenario", profile.scenario_key),
            ("scenario_file", profile.scenario_name),
            ("seed", profile.seed),
            ("action_space", profile.action_space_kind),
            ("frame_stack", profile.frame_stack),
            ("requested_steps", profile.requested_timesteps),
            ("effective_steps", profile.effective_timesteps),
            ("checkpoint_every", profile.checkpoint_frequency),
            ("eval_every", evaluation_settings.frequency),
            ("eval_episodes", evaluation_settings.episodes),
        ],
    )
    if profile.scenario_description:
        print_block("Scenario", [profile.scenario_description])
    print_kv_block(
        "Reward Shaping",
        [
            ("scale", profile.reward_shaping.scale),
            ("offset", profile.reward_shaping.offset),
            ("clip_min", profile.reward_shaping.clip_min),
            ("clip_max", profile.reward_shaping.clip_max),
        ],
    )
    if profile.uses_rounded_timesteps:
        print_block(
            "Timesteps Note",
            [
                "Stable-Baselines3 redondea al siguiente multiplo de n_steps.",
                f"n_steps={profile.n_steps} -> se ejecutaran {profile.effective_timesteps} pasos.",
            ],
        )

    if resume_state.is_resumed:
        resume_lines = [
            f"mode={resume_state.mode}",
            f"source={resume_state.resume_source}",
            f"saved_steps={resume_state.resume_saved_timesteps}",
        ]
        if resume_state.note:
            resume_lines.append(resume_state.note)
        print_block("Resume", resume_lines)
    else:
        if resume_state.mode == "from_scratch":
            print_block("Resume", ["Entrenamiento forzado desde cero."])
        elif resume_state.mode == AUTO_RESUME_MODE:
            print_block("Resume", ["No se encontro checkpoint compatible. El entrenamiento comienza desde cero."])
        else:
            print_block("Resume", ["Entrenamiento comenzando desde cero."])

    print_kv_block(
        "Artifacts",
        [
            ("auto_checkpoints", format_path_tail(checkpoints_dir)),
        ],
    )
    if profile.early_stopping.enabled:
        print_kv_block(
            "Early Stopping",
            [
                ("enabled", profile.early_stopping.enabled),
                ("patience", profile.early_stopping.patience_evaluations),
                ("min_evals", profile.early_stopping.min_evaluations),
                ("min_delta", profile.early_stopping.min_delta),
            ],
        )


def train_profile(
    profile_name: str,
    profile: TrainingProfile,
    *,
    resume_mode: str = AUTO_RESUME_MODE,
    from_scratch: bool = False,
    eval_frequency: int | None = None,
    eval_episodes: int | None = None,
    save_best: bool = True,
    allow_scenario_resume: bool = False,
    run_label: str | None = None,
) -> TrainingExecutionResult:
    from doom_agent.envs import make_vectorized_env
    from doom_agent.services.resume import resolve_resume_state
    from doom_agent.services.training_support import (
        EvaluationSettings,
        PeriodicTrainingCallback,
        load_training_model,
    )

    project_paths = build_project_paths()
    resolved_eval_frequency = profile.eval_frequency if eval_frequency is None else eval_frequency
    resolved_eval_episodes = profile.eval_episodes if eval_episodes is None else eval_episodes

    if resolved_eval_episodes <= 0:
        raise ValueError("'eval_episodes' debe ser mayor que cero.")
    if resolved_eval_frequency <= 0:
        raise ValueError("'eval_frequency' debe ser mayor que cero.")

    profile.validate(project_paths)

    ensure_directories(
        [
            project_paths.artifacts_dir,
            project_paths.runs_dir,
            project_paths.checkpoints_dir,
            project_paths.auto_checkpoints_dir,
            project_paths.tensorboard_dir,
            project_paths.videos_dir,
            project_paths.reports_dir,
        ]
    )

    resume_state = resolve_resume_state(
        project_paths,
        profile,
        resume_mode=resume_mode,
        from_scratch=from_scratch,
        allow_scenario_change=allow_scenario_resume,
    )
    evaluation_settings = EvaluationSettings(
        frequency=resolved_eval_frequency,
        episodes=resolved_eval_episodes,
        save_best=save_best,
        best_checkpoint_stem=project_paths.checkpoints_dir / f"{profile.checkpoint_name}_best",
        seed=profile.seed + 1,
    )

    final_checkpoint_stem = project_paths.checkpoints_dir / profile.checkpoint_name
    run_created_at = datetime.now(UTC)
    run_id = build_run_id(profile, run_created_at)
    run_artifacts = build_run_artifact_paths(project_paths, run_id)
    started_at = perf_counter()
    final_checkpoint_path = checkpoint_zip_path(final_checkpoint_stem)
    report_path: Path | None = None
    ensure_directories(
        [
            run_artifacts.run_dir,
            run_artifacts.checkpoints_dir,
            run_artifacts.tensorboard_dir,
            run_artifacts.videos_dir,
        ]
    )
    env = make_vectorized_env(profile, project_paths, video_dir=run_artifacts.videos_dir)
    env.seed(profile.seed)
    eval_profile = profile.for_evaluation(render=False).with_seed(profile.seed + 1)
    eval_env = make_vectorized_env(eval_profile, project_paths)
    eval_env.seed(eval_profile.seed)
    model = load_training_model(env, profile, run_artifacts.tensorboard_dir, resume_state)
    callback = PeriodicTrainingCallback(
        profile_name=profile_name,
        profile=profile,
        auto_checkpoint_dir=project_paths.auto_checkpoints_dir,
        evaluation_settings=evaluation_settings,
        eval_env=eval_env,
        resume_state=resume_state,
        verbose=1,
    )
    print_training_summary(
        profile_name,
        profile,
        project_paths.auto_checkpoints_dir,
        resume_state,
        evaluation_settings,
        run_label=run_label,
    )

    completed = False
    training_status = "interrupted"
    try:
        model.learn(
            total_timesteps=profile.effective_timesteps,
            tb_log_name=profile.tensorboard_run_name,
            callback=callback,
            reset_num_timesteps=not resume_state.is_resumed,
        )
        completed = True
        training_status = "completed"
        if callback.early_stopping.stopped:
            training_status = "early_stopped"
    except KeyboardInterrupt:
        print_block("Training Interrupted", ["Entrenamiento interrumpido por usuario.", "Guardando progreso..."])
        training_status = "keyboard_interrupt"
    except ViZDoomUnexpectedExitException:
        print_block("Training Interrupted", ["ViZDoom se cerro.", "Guardando progreso..."])
        training_status = "vizdoom_exit"
    finally:
        duration_seconds = perf_counter() - started_at
        metadata = build_checkpoint_metadata(
            profile_name=profile_name,
            profile=profile,
            saved_timesteps=model.num_timesteps,
            resume_source=resume_state.resume_source,
            resume_saved_timesteps=resume_state.resume_saved_timesteps,
            training_status=training_status,
            evaluation_metrics=callback.last_evaluation_metrics,
            is_best_checkpoint=False,
        )
        save_checkpoint_bundle(model, final_checkpoint_stem, metadata)
        copy_checkpoint_bundle(final_checkpoint_stem, run_artifacts.final_checkpoint_stem)
        try:
            env.close()
        except ViZDoomUnexpectedExitException:
            pass
        try:
            eval_env.close()
        except ViZDoomUnexpectedExitException:
            pass

        best_checkpoint_path = copy_run_best_checkpoint_if_updated(
            final_checkpoint_stem,
            run_artifacts.best_checkpoint_stem,
            best_checkpoint_updated=callback.best_checkpoint_updated,
        )
        report = build_training_run_report(
            run_id=run_id,
            created_at_utc=run_created_at.isoformat(),
            profile_name=profile_name,
            run_label=run_label,
            profile=profile,
            run_artifacts=run_artifacts,
            checkpoint_path=final_checkpoint_path,
            best_checkpoint_path=best_checkpoint_path,
            training_status=training_status,
            completed=completed,
            saved_timesteps=model.num_timesteps,
            resume_mode=resume_state.mode,
            resume_source=resume_state.resume_source,
            resume_saved_timesteps=resume_state.resume_saved_timesteps,
            evaluation_metrics=callback.last_evaluation_metrics,
            evaluation_history=callback.evaluation_history,
            duration_seconds=duration_seconds,
            stopped_early=callback.early_stopping.stopped,
            stop_reason=callback.early_stopping.stop_reason,
        )
        report_path = save_training_run_report(project_paths, report)
        _persist_run_report_to_database(report, report_path)
        _sync_run_artifacts_to_remote(run_id)

        print_kv_block(
            "Training Result",
            [
                ("status", training_status),
                ("saved_steps", model.num_timesteps),
                ("model", format_path_tail(final_checkpoint_stem.with_suffix(".zip"))),
                ("report", format_path_tail(report_path)),
            ],
        )
        if training_status == "early_stopped" and callback.early_stopping.stop_reason is not None:
            print_block("Stop Reason", [callback.early_stopping.stop_reason])
    if report_path is None:
        raise RuntimeError("No se pudo guardar el reporte de entrenamiento.")
    return TrainingExecutionResult(
        profile_name=profile_name,
        profile=profile,
        final_checkpoint_path=final_checkpoint_path,
        report_path=report_path,
        training_status=training_status,
        completed=completed,
        saved_timesteps=model.num_timesteps,
        stopped_early=callback.early_stopping.stopped,
        stop_reason=callback.early_stopping.stop_reason,
    )


def train(
    profile_name: str = "default",
    requested_timesteps: int | None = None,
    scenario_name: str | None = None,
    seed: int | None = None,
    *,
    resume_mode: str = AUTO_RESUME_MODE,
    from_scratch: bool = False,
    eval_frequency: int | None = None,
    eval_episodes: int | None = None,
    save_best: bool = True,
    allow_scenario_resume: bool = False,
) -> TrainingExecutionResult:
    profile = get_training_profile(
        profile_name,
        requested_timesteps=requested_timesteps,
        scenario_name=scenario_name,
        seed=seed,
    )
    if profile.curriculum:
        if scenario_name is not None:
            raise ValueError(
                "No puedes usar '--scenario' con un perfil de curriculum; las etapas ya definen sus escenarios."
            )
        stages = materialize_curriculum_profiles(
            profile_name=profile_name,
            requested_timesteps=requested_timesteps,
            seed=seed,
        )
        print(f"Ejecutando curriculum de {len(stages)} etapas.")
        stage_resume_mode = resume_mode
        stage_from_scratch = from_scratch
        last_result: TrainingExecutionResult | None = None

        for stage_index, stage_profile in enumerate(stages, start=1):
            last_result = train_profile(
                profile_name=profile_name,
                profile=stage_profile,
                resume_mode=stage_resume_mode,
                from_scratch=stage_from_scratch,
                eval_frequency=eval_frequency,
                eval_episodes=eval_episodes,
                save_best=save_best,
                allow_scenario_resume=stage_index > 1,
                run_label=f"curriculum:{stage_index}/{len(stages)}",
            )
            if last_result.training_status in {"keyboard_interrupt", "vizdoom_exit"}:
                break
            stage_resume_mode = str(select_resume_checkpoint_path(last_result))
            stage_from_scratch = False

        if last_result is None:
            raise RuntimeError("No se pudo ejecutar ninguna etapa del curriculum.")
        return last_result

    return train_profile(
        profile_name=profile_name,
        profile=profile,
        resume_mode=resume_mode,
        from_scratch=from_scratch,
        eval_frequency=eval_frequency,
        eval_episodes=eval_episodes,
        save_best=save_best,
        allow_scenario_resume=allow_scenario_resume,
    )
