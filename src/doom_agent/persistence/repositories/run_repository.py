from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from doom_agent.persistence.enums import (
    ArtifactRole,
    ArtifactType,
    SyncEventStatus,
    SyncStatus,
)
from doom_agent.persistence.models import RunArtifact, SyncEvent, TrainingRun
from doom_agent.persistence.session import create_session_factory
from doom_agent.shared.contracts import ExperimentIndexEntryPayload, TrainingRunReportPayload


@dataclass(frozen=True, slots=True)
class RunArtifactRecord:
    artifact_type: str
    local_path: Path
    artifact_role: str | None = None
    metadata_json: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class SyncCandidateArtifact:
    artifact_id: int
    run_id: str
    artifact_type: str
    artifact_role: str | None
    local_path: Path
    run_local_dir: Path


@dataclass(frozen=True, slots=True)
class ArtifactReplacementSummary:
    inventory_changed: bool
    has_unsynced_artifacts: bool


def build_run_artifact_records(
    report: TrainingRunReportPayload,
    *,
    report_path: Path,
) -> list[RunArtifactRecord]:
    records = [
        RunArtifactRecord(
            artifact_type=ArtifactType.REPORT.value,
            artifact_role=ArtifactRole.SUMMARY.value,
            local_path=report_path,
        ),
        RunArtifactRecord(
            artifact_type=ArtifactType.REPORT.value,
            local_path=Path(report["manifest_path"]),
            metadata_json={
                "sidecar_kind": "manifest",
            },
        ),
        RunArtifactRecord(
            artifact_type=ArtifactType.CHECKPOINT.value,
            artifact_role=ArtifactRole.FINAL.value,
            local_path=Path(report["checkpoint_archive_path"]),
            metadata_json={
                "canonical_checkpoint_path": report["checkpoint_path"],
                "checkpoint_metadata_path": str(
                    Path(report["checkpoint_archive_path"]).with_suffix(".json")
                ),
            },
        ),
        RunArtifactRecord(
            artifact_type=ArtifactType.CHECKPOINT.value,
            artifact_role=ArtifactRole.FINAL.value,
            local_path=Path(report["checkpoint_archive_path"]).with_suffix(".json"),
            metadata_json={
                "canonical_checkpoint_path": report["checkpoint_path"],
                "sidecar_kind": "metadata",
            },
        ),
    ]
    best_checkpoint_archive_path = report["best_checkpoint_archive_path"]
    if best_checkpoint_archive_path is not None:
        best_checkpoint_path = Path(best_checkpoint_archive_path)
        records.append(
            RunArtifactRecord(
                artifact_type=ArtifactType.CHECKPOINT.value,
                artifact_role=ArtifactRole.BEST.value,
                local_path=best_checkpoint_path,
                metadata_json={
                    "canonical_checkpoint_path": report["best_checkpoint_path"],
                    "checkpoint_metadata_path": str(best_checkpoint_path.with_suffix(".json")),
                },
            )
        )
        records.append(
            RunArtifactRecord(
                artifact_type=ArtifactType.CHECKPOINT.value,
                artifact_role=ArtifactRole.BEST.value,
                local_path=best_checkpoint_path.with_suffix(".json"),
                metadata_json={
                    "canonical_checkpoint_path": report["best_checkpoint_path"],
                    "sidecar_kind": "metadata",
                },
            )
        )
    for selected_auto_checkpoint_archive_path in report["selected_auto_checkpoint_archive_paths"]:
        selected_auto_checkpoint_path = Path(selected_auto_checkpoint_archive_path)
        records.append(
            RunArtifactRecord(
                artifact_type=ArtifactType.CHECKPOINT.value,
                artifact_role=ArtifactRole.AUTO.value,
                local_path=selected_auto_checkpoint_path,
                metadata_json={
                    "canonical_checkpoint_path": str(selected_auto_checkpoint_path),
                    "checkpoint_metadata_path": str(
                        selected_auto_checkpoint_path.with_suffix(".json")
                    ),
                    "selection_policy": "latest_only",
                },
            )
        )
        records.append(
            RunArtifactRecord(
                artifact_type=ArtifactType.CHECKPOINT.value,
                artifact_role=ArtifactRole.AUTO.value,
                local_path=selected_auto_checkpoint_path.with_suffix(".json"),
                metadata_json={
                    "canonical_checkpoint_path": str(selected_auto_checkpoint_path),
                    "sidecar_kind": "metadata",
                    "selection_policy": "latest_only",
                },
            )
        )
    records.extend(_discover_video_artifact_records(report))
    return records


def _extract_mean_reward(report: TrainingRunReportPayload) -> float | None:
    evaluation_metrics = report["evaluation_metrics"]
    if evaluation_metrics is None:
        return None
    return evaluation_metrics["mean_reward"]


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _artifact_size(path: Path) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    return path.stat().st_size


def _cast_metadata(metadata: dict[str, object] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    return dict(metadata)


def _cast_evaluation_metrics(
    evaluation_metrics: Mapping[str, object] | None,
) -> dict[str, Any] | None:
    if evaluation_metrics is None:
        return None
    return dict(evaluation_metrics)


def _discover_video_artifact_records(
    report: TrainingRunReportPayload,
) -> list[RunArtifactRecord]:
    video_dir = Path(report["videos_dir"])
    if not video_dir.exists() or not video_dir.is_dir():
        return []

    records: list[RunArtifactRecord] = []
    for video_path in sorted(video_dir.glob("*.mp4")):
        records.append(
            RunArtifactRecord(
                artifact_type=ArtifactType.VIDEO.value,
                local_path=video_path,
                metadata_json={
                    "file_name": video_path.name,
                },
            )
        )
    return records


class TrainingRunRepository:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or create_session_factory()

    def upsert_run_report(
        self,
        report: TrainingRunReportPayload,
        *,
        report_path: Path,
    ) -> None:
        session = self._session_factory()
        try:
            training_run = session.get(TrainingRun, report["run_id"])
            if training_run is None:
                training_run = TrainingRun(run_id=report["run_id"])
            previous_sync_status = getattr(training_run, "sync_status", None)

            artifact_summary = self._replace_artifacts(
                training_run,
                build_run_artifact_records(report, report_path=report_path),
            )
            self._apply_report(
                training_run,
                report,
                report_path,
                previous_sync_status=previous_sync_status,
                artifact_summary=artifact_summary,
            )
            session.add(training_run)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_run(self, run_id: str) -> TrainingRun | None:
        session = self._session_factory()
        try:
            return session.get(TrainingRun, run_id)
        finally:
            session.close()

    def list_runs(self, *, limit: int = 20) -> list[TrainingRun]:
        session = self._session_factory()
        try:
            statement = select(TrainingRun).order_by(TrainingRun.created_at_utc.desc()).limit(limit)
            return list(session.scalars(statement))
        finally:
            session.close()

    def list_run_entries(self, *, limit: int = 20) -> list[ExperimentIndexEntryPayload]:
        session = self._session_factory()
        try:
            statement = (
                select(TrainingRun)
                .options(selectinload(TrainingRun.artifacts))
                .order_by(TrainingRun.created_at_utc.desc())
                .limit(limit)
            )
            runs = list(session.scalars(statement))
            return [_build_experiment_index_entry(run) for run in runs]
        finally:
            session.close()

    def list_run_ids_by_sync_status(self, *, sync_status: str, limit: int = 20) -> list[str]:
        session = self._session_factory()
        try:
            statement = (
                select(TrainingRun.run_id)
                .where(TrainingRun.sync_status == sync_status)
                .order_by(TrainingRun.created_at_utc.desc())
                .limit(limit)
            )
            return [str(run_id) for run_id in session.scalars(statement)]
        finally:
            session.close()

    def list_sync_candidates(self, run_id: str) -> list[SyncCandidateArtifact]:
        session = self._session_factory()
        try:
            statement = (
                select(RunArtifact, TrainingRun.local_run_dir)
                .join(TrainingRun, TrainingRun.run_id == RunArtifact.run_id)
                .where(
                    RunArtifact.run_id == run_id,
                    RunArtifact.artifact_type.in_(
                        (
                            ArtifactType.CHECKPOINT.value,
                            ArtifactType.REPORT.value,
                            ArtifactType.VIDEO.value,
                        )
                    ),
                    RunArtifact.sync_status != SyncStatus.SYNCED.value,
                )
                .order_by(RunArtifact.artifact_id.asc())
            )
            rows = session.execute(statement).all()
            return [
                SyncCandidateArtifact(
                    artifact_id=artifact.artifact_id,
                    run_id=artifact.run_id,
                    artifact_type=artifact.artifact_type,
                    artifact_role=artifact.artifact_role,
                    local_path=Path(artifact.local_path),
                    run_local_dir=Path(local_run_dir),
                )
                for artifact, local_run_dir in rows
            ]
        finally:
            session.close()

    def mark_run_sync_pending(self, run_id: str) -> None:
        self.update_run_sync_status(run_id, SyncStatus.PENDING.value)

    def update_run_sync_status(self, run_id: str, sync_status: str) -> None:
        session = self._session_factory()
        try:
            training_run = session.get(TrainingRun, run_id)
            if training_run is None:
                raise RuntimeError(f"Corrida no encontrada para sync: {run_id}")
            training_run.sync_status = sync_status
            training_run.last_sync_at_utc = datetime.now(UTC)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_artifact_sync_pending(self, artifact_id: int) -> None:
        session = self._session_factory()
        try:
            artifact = _get_artifact(session, artifact_id)
            artifact.sync_status = SyncStatus.PENDING.value
            artifact.sync_error = None
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_artifact_synced(
        self,
        artifact_id: int,
        *,
        storage_backend: str,
        bucket_name: str,
        object_key: str,
        remote_uri: str,
    ) -> None:
        session = self._session_factory()
        try:
            artifact = _get_artifact(session, artifact_id)
            artifact.storage_backend = storage_backend
            artifact.bucket_name = bucket_name
            artifact.object_key = object_key
            artifact.remote_uri = remote_uri
            artifact.sync_status = SyncStatus.SYNCED.value
            artifact.sync_error = None
            artifact.uploaded_at_utc = datetime.now(UTC)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_artifact_failed(self, artifact_id: int, error_message: str) -> None:
        session = self._session_factory()
        try:
            artifact = _get_artifact(session, artifact_id)
            artifact.sync_status = SyncStatus.FAILED.value
            artifact.sync_error = error_message
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_sync_event_start(
        self,
        *,
        run_id: str,
        artifact_id: int,
        operation: str,
        details_json: dict[str, Any] | None = None,
    ) -> int:
        session = self._session_factory()
        try:
            attempt_number = _next_sync_attempt_number(
                session,
                run_id=run_id,
                artifact_id=artifact_id,
                operation=operation,
            )
            event = SyncEvent(
                run_id=run_id,
                artifact_id=artifact_id,
                operation=operation,
                status=SyncEventStatus.STARTED.value,
                attempt_number=attempt_number,
                started_at=datetime.now(UTC),
                details_json=details_json,
            )
            session.add(event)
            session.commit()
            return event.event_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_sync_event_succeeded(
        self,
        event_id: int,
        *,
        details_json: dict[str, Any] | None = None,
    ) -> None:
        self._finish_sync_event(
            event_id,
            status=SyncEventStatus.SUCCEEDED.value,
            details_json=details_json,
        )

    def mark_sync_event_failed(
        self,
        event_id: int,
        *,
        error_message: str,
        details_json: dict[str, Any] | None = None,
    ) -> None:
        self._finish_sync_event(
            event_id,
            status=SyncEventStatus.FAILED.value,
            error_message=error_message,
            details_json=details_json,
        )

    def _apply_report(
        self,
        training_run: TrainingRun,
        report: TrainingRunReportPayload,
        report_path: Path,
        *,
        previous_sync_status: str | None,
        artifact_summary: ArtifactReplacementSummary,
    ) -> None:
        training_run.profile_name = report["profile_name"]
        training_run.run_label = report["run_label"]
        training_run.scenario_key = report["scenario_key"]
        training_run.scenario_name = report["scenario_name"]
        training_run.checkpoint_name = report["checkpoint_name"]
        training_run.seed = report["seed"]
        training_run.requested_timesteps = report["requested_timesteps"]
        training_run.effective_timesteps = report["effective_timesteps"]
        training_run.saved_timesteps = report["saved_timesteps"]
        training_run.training_status = report["training_status"]
        training_run.completed = report["completed"]
        training_run.stopped_early = report["stopped_early"]
        training_run.stop_reason = report["stop_reason"]
        training_run.resume_mode = report["resume_mode"]
        training_run.resume_source = report["resume_source"]
        training_run.resume_saved_timesteps = report["resume_saved_timesteps"]
        training_run.evaluation_metrics = _cast_evaluation_metrics(report["evaluation_metrics"])
        training_run.mean_reward = _extract_mean_reward(report)
        training_run.duration_seconds = report["duration_seconds"]
        training_run.local_run_dir = report["run_dir"]
        training_run.local_report_path = str(report_path)
        training_run.sync_status = _next_run_sync_status(
            previous_sync_status=previous_sync_status,
            artifact_summary=artifact_summary,
        )
        training_run.created_at_utc = _parse_datetime(report["created_at_utc"])
        training_run.finished_at_utc = datetime.now(UTC)

    def _replace_artifacts(
        self,
        training_run: TrainingRun,
        artifact_records: list[RunArtifactRecord],
    ) -> ArtifactReplacementSummary:
        existing_by_key = {
            _artifact_identity(artifact): artifact for artifact in training_run.artifacts
        }
        next_artifacts: list[RunArtifact] = []
        inventory_changed = len(existing_by_key) != len(artifact_records)
        has_unsynced_artifacts = False

        for record in artifact_records:
            artifact_key = _artifact_record_identity(record)
            existing_artifact = existing_by_key.pop(artifact_key, None)
            next_file_size = _artifact_size(record.local_path)
            next_metadata = _cast_metadata(record.metadata_json)
            if existing_artifact is None:
                inventory_changed = True
                next_artifacts.append(
                    RunArtifact(
                        artifact_type=record.artifact_type,
                        artifact_role=record.artifact_role,
                        local_path=str(record.local_path),
                        file_size_bytes=next_file_size,
                        metadata_json=next_metadata,
                        sync_status=SyncStatus.LOCAL_ONLY.value,
                    )
                )
                has_unsynced_artifacts = True
                continue

            artifact_changed = (
                existing_artifact.file_size_bytes != next_file_size
                or existing_artifact.metadata_json != next_metadata
            )
            if artifact_changed:
                inventory_changed = True
                existing_artifact.storage_backend = None
                existing_artifact.bucket_name = None
                existing_artifact.object_key = None
                existing_artifact.remote_uri = None
                existing_artifact.uploaded_at_utc = None
                existing_artifact.sync_error = None
                existing_artifact.sync_status = SyncStatus.LOCAL_ONLY.value

            existing_artifact.file_size_bytes = next_file_size
            existing_artifact.metadata_json = next_metadata
            has_unsynced_artifacts = has_unsynced_artifacts or (
                existing_artifact.sync_status != SyncStatus.SYNCED.value
            )
            next_artifacts.append(existing_artifact)

        if existing_by_key:
            inventory_changed = True
            has_unsynced_artifacts = True

        training_run.artifacts[:] = next_artifacts
        return ArtifactReplacementSummary(
            inventory_changed=inventory_changed,
            has_unsynced_artifacts=has_unsynced_artifacts,
        )

    def _finish_sync_event(
        self,
        event_id: int,
        *,
        status: str,
        error_message: str | None = None,
        details_json: dict[str, Any] | None = None,
    ) -> None:
        session = self._session_factory()
        try:
            event = session.get(SyncEvent, event_id)
            if event is None:
                raise RuntimeError(f"Evento de sync no encontrado: {event_id}")
            event.status = status
            event.finished_at = datetime.now(UTC)
            event.error_message = error_message
            event.details_json = details_json
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _build_experiment_index_entry(training_run: TrainingRun) -> ExperimentIndexEntryPayload:
    final_checkpoint_artifact = _find_artifact(
        training_run,
        ArtifactType.CHECKPOINT.value,
        ArtifactRole.FINAL.value,
    )
    best_checkpoint_artifact = _find_artifact(
        training_run,
        ArtifactType.CHECKPOINT.value,
        ArtifactRole.BEST.value,
    )
    return {
        "run_id": training_run.run_id,
        "created_at_utc": training_run.created_at_utc.isoformat(),
        "profile_name": training_run.profile_name,
        "run_label": training_run.run_label,
        "scenario_key": training_run.scenario_key,
        "checkpoint_name": training_run.checkpoint_name,
        "checkpoint_path": _required_artifact_metadata_value(
            final_checkpoint_artifact,
            "canonical_checkpoint_path",
        ),
        "best_checkpoint_path": _artifact_metadata_value(
            best_checkpoint_artifact,
            "canonical_checkpoint_path",
        ),
        "checkpoint_archive_path": _artifact_path(final_checkpoint_artifact),
        "best_checkpoint_archive_path": _artifact_path(best_checkpoint_artifact),
        "saved_timesteps": training_run.saved_timesteps,
        "training_status": training_run.training_status,
        "mean_reward": training_run.mean_reward,
        "seed": training_run.seed,
        "report_path": training_run.local_report_path,
    }


def _find_artifact(
    training_run: TrainingRun,
    artifact_type: str,
    artifact_role: str | None,
) -> RunArtifact | None:
    metadata_sidecar_match: RunArtifact | None = None
    for artifact in training_run.artifacts:
        if artifact.artifact_type == artifact_type and artifact.artifact_role == artifact_role:
            if not _is_metadata_sidecar(artifact):
                return artifact
            if metadata_sidecar_match is None:
                metadata_sidecar_match = artifact
    return metadata_sidecar_match


def _is_metadata_sidecar(artifact: RunArtifact) -> bool:
    if artifact.metadata_json is None:
        return False
    sidecar_kind = artifact.metadata_json.get("sidecar_kind")
    return sidecar_kind == "metadata"


def _artifact_path(artifact: RunArtifact | None) -> str:
    if artifact is None:
        return ""
    return artifact.local_path


def _artifact_metadata_value(artifact: RunArtifact | None, key: str) -> str | None:
    if artifact is None or artifact.metadata_json is None:
        return None
    value = artifact.metadata_json.get(key)
    if value is None:
        return None
    return str(value)


def _required_artifact_metadata_value(artifact: RunArtifact | None, key: str) -> str:
    value = _artifact_metadata_value(artifact, key)
    if value is None:
        return ""
    return value


def _artifact_record_identity(record: RunArtifactRecord) -> tuple[str, str | None, str]:
    return (record.artifact_type, record.artifact_role, str(record.local_path))


def _artifact_identity(artifact: RunArtifact) -> tuple[str, str | None, str]:
    return (artifact.artifact_type, artifact.artifact_role, artifact.local_path)


def _next_run_sync_status(
    *,
    previous_sync_status: str | None,
    artifact_summary: ArtifactReplacementSummary,
) -> str:
    if artifact_summary.has_unsynced_artifacts:
        return SyncStatus.LOCAL_ONLY.value
    if previous_sync_status is None:
        return SyncStatus.LOCAL_ONLY.value
    return previous_sync_status


def _get_artifact(session: Session, artifact_id: int) -> RunArtifact:
    artifact = session.get(RunArtifact, artifact_id)
    if artifact is None:
        raise RuntimeError(f"Artefacto no encontrado: {artifact_id}")
    return artifact


def _next_sync_attempt_number(
    session: Session,
    *,
    run_id: str,
    artifact_id: int,
    operation: str,
) -> int:
    statement = select(func.max(SyncEvent.attempt_number)).where(
        SyncEvent.run_id == run_id,
        SyncEvent.artifact_id == artifact_id,
        SyncEvent.operation == operation,
    )
    max_attempt = session.scalar(statement)
    if max_attempt is None:
        return 1
    return int(max_attempt) + 1
