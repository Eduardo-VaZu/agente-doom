from __future__ import annotations

from pathlib import Path
from typing import cast

from doom_agent.config import build_project_paths
from doom_agent.persistence import has_explicit_database_url
from doom_agent.persistence.repositories import TrainingRunRepository
from doom_agent.shared.contracts import (
    EvaluationMetricsPayload,
    RunInspectionPayload,
    RunManifestPayload,
    TrainingRunReportPayload,
)
from doom_agent.utils.filesystem import read_json
from doom_agent.utils.reports import load_training_run_report_from_path, report_path_for_run


def inspect_run(run_id: str, *, root_dir: Path | None = None) -> RunInspectionPayload:
    project_paths = build_project_paths(root_dir=root_dir)
    report_path = report_path_for_run(project_paths, run_id)
    sync_status: str | None = None

    if has_explicit_database_url():
        try:
            training_run = TrainingRunRepository().get_run(run_id)
        except Exception:
            training_run = None
        if training_run is not None:
            sync_status = training_run.sync_status
            database_report_path = Path(training_run.local_report_path)
            if not report_path.exists() and database_report_path.exists():
                report_path = database_report_path

    if not report_path.exists():
        raise FileNotFoundError(f"No se encontro report.json para corrida: {run_id}")

    report = load_training_run_report_from_path(report_path)
    manifest_path = _resolve_manifest_path(report, report_path)
    manifest = _load_manifest(manifest_path)

    evaluation_metrics = report["evaluation_metrics"]
    selected_auto_checkpoint_archive_paths = list(
        report.get("selected_auto_checkpoint_archive_paths", [])
    )
    final_checkpoint_path = Path(report["checkpoint_archive_path"])
    best_checkpoint_archive_path = report["best_checkpoint_archive_path"]
    best_checkpoint_path = (
        None if best_checkpoint_archive_path is None else Path(best_checkpoint_archive_path)
    )
    evaluation_history = report["evaluation_history"]
    remote_sync_candidates = _remote_sync_candidates(manifest)

    return {
        "run_id": report["run_id"],
        "created_at_utc": report["created_at_utc"],
        "profile_name": report["profile_name"],
        "run_label": report["run_label"],
        "scenario_key": report["scenario_key"],
        "scenario_name": report["scenario_name"],
        "checkpoint_name": report["checkpoint_name"],
        "seed": report["seed"],
        "requested_timesteps": report["requested_timesteps"],
        "effective_timesteps": report["effective_timesteps"],
        "saved_timesteps": report["saved_timesteps"],
        "training_status": report["training_status"],
        "completed": report["completed"],
        "sync_status": sync_status,
        "mean_reward": _metric_value(evaluation_metrics, "mean_reward"),
        "std_reward": _metric_value(evaluation_metrics, "std_reward"),
        "mean_episode_length": _metric_value(evaluation_metrics, "mean_episode_length"),
        "evaluation_episodes": _metric_int_value(evaluation_metrics, "episodes"),
        "evaluation_history_count": len(evaluation_history),
        "latest_evaluation_step": (
            None if not evaluation_history else evaluation_history[-1]["step"]
        ),
        "report_path": str(report_path),
        "report_exists": report_path.exists(),
        "manifest_path": str(manifest_path),
        "manifest_exists": manifest_path.exists(),
        "checkpoint_archive_path": str(final_checkpoint_path),
        "checkpoint_archive_exists": final_checkpoint_path.exists(),
        "best_checkpoint_archive_path": best_checkpoint_archive_path,
        "best_checkpoint_archive_exists": (
            False if best_checkpoint_path is None else best_checkpoint_path.exists()
        ),
        "selected_auto_checkpoint_archive_paths": selected_auto_checkpoint_archive_paths,
        "selected_auto_checkpoint_count": len(selected_auto_checkpoint_archive_paths),
        "remote_sync_candidates": remote_sync_candidates,
        "remote_sync_candidate_count": len(remote_sync_candidates),
        "handoff_ready": (
            report_path.exists()
            and manifest_path.exists()
            and final_checkpoint_path.exists()
        ),
    }


def _resolve_manifest_path(report: TrainingRunReportPayload, report_path: Path) -> Path:
    manifest_path_value = report.get("manifest_path")
    if isinstance(manifest_path_value, str) and manifest_path_value:
        candidate = Path(manifest_path_value)
        if candidate.exists():
            return candidate
    return report_path.parent / "manifest.json"


def _load_manifest(manifest_path: Path) -> RunManifestPayload | None:
    if not manifest_path.exists():
        return None
    return cast(RunManifestPayload, read_json(manifest_path))


def _metric_value(
    evaluation_metrics: EvaluationMetricsPayload | None,
    key: str,
) -> float | int | None:
    if evaluation_metrics is None:
        return None
    return cast(float | int | None, evaluation_metrics.get(key))


def _metric_int_value(
    evaluation_metrics: EvaluationMetricsPayload | None,
    key: str,
) -> int | None:
    if evaluation_metrics is None:
        return None
    value = evaluation_metrics.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Valor no soportado para metrica entera: {type(value).__name__}")


def _remote_sync_candidates(manifest: RunManifestPayload | None) -> list[str]:
    if manifest is None:
        return []
    return [
        artifact["relative_path"]
        for artifact in manifest["artifacts"]
        if artifact.get("remote_sync_candidate") is True
    ]
