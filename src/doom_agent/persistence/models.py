from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doom_agent.persistence.base import Base, TimestampedModel
from doom_agent.persistence.enums import (
    ArtifactRole,
    ArtifactType,
    SyncEventStatus,
    SyncOperation,
    SyncStatus,
)


class TrainingRun(TimestampedModel, Base):
    __tablename__ = "training_runs"
    __table_args__ = (
        Index("ix_training_runs_scenario_created_at", "scenario_key", "created_at_utc"),
        Index("ix_training_runs_status_created_at", "training_status", "created_at_utc"),
        Index("ix_training_runs_sync_status_created_at", "sync_status", "created_at_utc"),
        CheckConstraint(
            "training_status IN ('completed', 'early_stopped', 'interrupted', "
            "'keyboard_interrupt', 'vizdoom_exit')",
            name="training_status",
        ),
        CheckConstraint(
            "sync_status IN ('local_only', 'pending', 'synced', 'failed')",
            name="sync_status",
        ),
    )

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    profile_name: Mapped[str] = mapped_column(String(120), nullable=False)
    run_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scenario_key: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checkpoint_name: Mapped[str] = mapped_column(String(255), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_timesteps: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_timesteps: Mapped[int] = mapped_column(Integer, nullable=False)
    saved_timesteps: Mapped[int] = mapped_column(Integer, nullable=False)
    training_status: Mapped[str] = mapped_column(String(40), nullable=False)
    completed: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)
    stopped_early: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=False)
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_mode: Mapped[str] = mapped_column(String(80), nullable=False)
    resume_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_saved_timesteps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    mean_reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    local_run_dir: Mapped[str] = mapped_column(Text, nullable=False)
    local_report_path: Mapped[str] = mapped_column(Text, nullable=False)
    sync_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=SyncStatus.LOCAL_ONLY.value,
    )
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    artifacts: Mapped[list[RunArtifact]] = relationship(
        back_populates="training_run",
        cascade="all, delete-orphan",
    )
    sync_events: Mapped[list[SyncEvent]] = relationship(
        back_populates="training_run",
        cascade="all, delete-orphan",
    )


class RunArtifact(TimestampedModel, Base):
    __tablename__ = "run_artifacts"
    __table_args__ = (
        Index("ix_run_artifacts_run_type", "run_id", "artifact_type"),
        Index("ix_run_artifacts_sync_status", "sync_status"),
        UniqueConstraint("remote_uri", name="uq_run_artifacts_remote_uri"),
        CheckConstraint(
            "artifact_type IN ('checkpoint', 'video', 'tensorboard', 'report')",
            name="artifact_type",
        ),
        CheckConstraint(
            "artifact_role IS NULL OR artifact_role IN ('final', 'best', 'auto', 'eval', 'summary')",
            name="artifact_role",
        ),
        CheckConstraint(
            "sync_status IN ('local_only', 'pending', 'synced', 'failed')",
            name="sync_status",
        ),
    )

    artifact_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("training_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    artifact_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_backend: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bucket_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    remote_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    sync_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=SyncStatus.PENDING.value,
    )
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    training_run: Mapped[TrainingRun] = relationship(back_populates="artifacts")
    sync_events: Mapped[list[SyncEvent]] = relationship(
        back_populates="artifact",
        cascade="all, delete-orphan",
    )


class SyncEvent(TimestampedModel, Base):
    __tablename__ = "sync_events"
    __table_args__ = (
        Index("ix_sync_events_run_started_at", "run_id", "started_at"),
        Index("ix_sync_events_artifact_started_at", "artifact_id", "started_at"),
        CheckConstraint(
            "operation IN ('upload', 'download', 'verify', 'resync')",
            name="operation",
        ),
        CheckConstraint(
            "status IN ('started', 'succeeded', 'failed')",
            name="status",
        ),
    )

    event_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("training_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_id: Mapped[int | None] = mapped_column(
        BIGINT,
        ForeignKey("run_artifacts.artifact_id", ondelete="CASCADE"),
        nullable=True,
    )
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    training_run: Mapped[TrainingRun] = relationship(back_populates="sync_events")
    artifact: Mapped[RunArtifact | None] = relationship(back_populates="sync_events")


__all__ = [
    "ArtifactRole",
    "ArtifactType",
    "RunArtifact",
    "SyncEvent",
    "SyncEventStatus",
    "SyncOperation",
    "SyncStatus",
    "TrainingRun",
]
