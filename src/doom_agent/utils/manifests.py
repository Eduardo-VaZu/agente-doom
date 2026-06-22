from __future__ import annotations

from pathlib import Path

from doom_agent.shared.contracts import (
    RunManifestArtifactPayload,
    RunManifestPayload,
    TrainingRunReportPayload,
)
from doom_agent.storage import RunArtifactPaths
from doom_agent.utils.filesystem import write_json

MANIFEST_VERSION = 1


def build_run_manifest(
    report: TrainingRunReportPayload,
    *,
    run_artifacts: RunArtifactPaths,
    report_path: Path,
) -> RunManifestPayload:
    selected_auto_relative_paths = {
        Path(checkpoint_path).relative_to(run_artifacts.run_dir).as_posix()
        for checkpoint_path in report["selected_auto_checkpoint_archive_paths"]
    }
    selected_auto_relative_paths.update(
        {
            Path(relative_path).with_suffix(".json").as_posix()
            for relative_path in selected_auto_relative_paths
        }
    )

    artifacts: list[RunManifestArtifactPayload] = [
        _manifest_artifact_entry(
            run_artifacts.run_dir,
            report_path,
            artifact_type="report",
            artifact_role="summary",
            remote_sync_candidate=True,
        ),
        _manifest_artifact_entry(
            run_artifacts.run_dir,
            run_artifacts.manifest_path,
            artifact_type="manifest",
            remote_sync_candidate=True,
            exists=True,
        ),
        _manifest_artifact_entry(
            run_artifacts.run_dir,
            Path(report["checkpoint_archive_path"]),
            artifact_type="checkpoint",
            artifact_role="final",
            remote_sync_candidate=True,
        ),
        _manifest_artifact_entry(
            run_artifacts.run_dir,
            Path(report["checkpoint_archive_path"]).with_suffix(".json"),
            artifact_type="checkpoint",
            artifact_role="final",
            sidecar_kind="metadata",
            remote_sync_candidate=True,
        ),
    ]

    best_checkpoint_archive_path = report["best_checkpoint_archive_path"]
    if best_checkpoint_archive_path is not None:
        best_checkpoint_path = Path(best_checkpoint_archive_path)
        artifacts.extend(
            [
                _manifest_artifact_entry(
                    run_artifacts.run_dir,
                    best_checkpoint_path,
                    artifact_type="checkpoint",
                    artifact_role="best",
                    remote_sync_candidate=True,
                ),
                _manifest_artifact_entry(
                    run_artifacts.run_dir,
                    best_checkpoint_path.with_suffix(".json"),
                    artifact_type="checkpoint",
                    artifact_role="best",
                    sidecar_kind="metadata",
                    remote_sync_candidate=True,
                ),
            ]
        )

    artifacts.extend(
        _discover_manifest_entries(
            run_artifacts.run_dir,
            run_artifacts.videos_dir,
            artifact_type="video",
            remote_sync_candidate=True,
            pattern="*.mp4",
        )
    )
    artifacts.extend(
        _discover_auto_manifest_entries(
            run_artifacts.run_dir,
            run_artifacts.auto_checkpoints_dir,
            selected_relative_paths=selected_auto_relative_paths,
            pattern="*.zip",
        )
    )
    artifacts.extend(
        _discover_auto_manifest_entries(
            run_artifacts.run_dir,
            run_artifacts.auto_checkpoints_dir,
            selected_relative_paths=selected_auto_relative_paths,
            pattern="*.json",
            sidecar_kind="metadata",
        )
    )

    artifacts.sort(key=lambda artifact: artifact["relative_path"])
    return {
        "manifest_version": MANIFEST_VERSION,
        "run_id": report["run_id"],
        "created_at_utc": report["created_at_utc"],
        "profile_name": report["profile_name"],
        "run_label": report["run_label"],
        "profile": report["profile"],
        "scenario_key": report["scenario_key"],
        "scenario_name": report["scenario_name"],
        "checkpoint_name": report["checkpoint_name"],
        "seed": report["seed"],
        "requested_timesteps": report["requested_timesteps"],
        "effective_timesteps": report["effective_timesteps"],
        "saved_timesteps": report["saved_timesteps"],
        "training_status": report["training_status"],
        "completed": report["completed"],
        "evaluation_metrics": report["evaluation_metrics"],
        "artifacts": artifacts,
    }


def save_run_manifest(
    run_artifacts: RunArtifactPaths,
    manifest: RunManifestPayload,
) -> Path:
    write_json(run_artifacts.manifest_path, manifest)
    return run_artifacts.manifest_path


def _manifest_artifact_entry(
    run_dir: Path,
    artifact_path: Path,
    *,
    artifact_type: str,
    remote_sync_candidate: bool,
    artifact_role: str | None = None,
    sidecar_kind: str | None = None,
    exists: bool | None = None,
) -> RunManifestArtifactPayload:
    artifact_exists = artifact_path.exists() if exists is None else exists
    file_size_bytes = None
    if artifact_exists and artifact_path.exists() and artifact_path.is_file():
        file_size_bytes = artifact_path.stat().st_size
    return {
        "relative_path": artifact_path.relative_to(run_dir).as_posix(),
        "artifact_type": artifact_type,
        "artifact_role": artifact_role,
        "sidecar_kind": sidecar_kind,
        "remote_sync_candidate": remote_sync_candidate,
        "exists": artifact_exists,
        "file_size_bytes": file_size_bytes,
    }


def _discover_manifest_entries(
    run_dir: Path,
    search_dir: Path,
    *,
    artifact_type: str,
    remote_sync_candidate: bool,
    pattern: str,
    artifact_role: str | None = None,
    sidecar_kind: str | None = None,
) -> list[RunManifestArtifactPayload]:
    if not search_dir.exists() or not search_dir.is_dir():
        return []

    return [
        _manifest_artifact_entry(
            run_dir,
            artifact_path,
            artifact_type=artifact_type,
            artifact_role=artifact_role,
            sidecar_kind=sidecar_kind,
            remote_sync_candidate=remote_sync_candidate,
        )
        for artifact_path in sorted(search_dir.glob(pattern))
    ]


def _discover_auto_manifest_entries(
    run_dir: Path,
    auto_checkpoints_dir: Path,
    *,
    selected_relative_paths: set[str],
    pattern: str,
    sidecar_kind: str | None = None,
) -> list[RunManifestArtifactPayload]:
    if not auto_checkpoints_dir.exists() or not auto_checkpoints_dir.is_dir():
        return []

    entries: list[RunManifestArtifactPayload] = []
    for artifact_path in sorted(auto_checkpoints_dir.glob(pattern)):
        relative_path = artifact_path.relative_to(run_dir).as_posix()
        entries.append(
            _manifest_artifact_entry(
                run_dir,
                artifact_path,
                artifact_type="checkpoint",
                artifact_role="auto",
                sidecar_kind=sidecar_kind,
                remote_sync_candidate=relative_path in selected_relative_paths,
            )
        )
    return entries
