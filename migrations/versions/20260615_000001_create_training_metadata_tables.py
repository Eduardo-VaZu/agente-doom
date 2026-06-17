"""create training metadata tables

Revision ID: 20260615_000001
Revises:
Create Date: 2026-06-15 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260615_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_runs",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("profile_name", sa.String(length=120), nullable=False),
        sa.Column("run_label", sa.String(length=200), nullable=True),
        sa.Column("scenario_key", sa.String(length=80), nullable=False),
        sa.Column("scenario_name", sa.String(length=255), nullable=False),
        sa.Column("checkpoint_name", sa.String(length=255), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("requested_timesteps", sa.Integer(), nullable=False),
        sa.Column("effective_timesteps", sa.Integer(), nullable=False),
        sa.Column("saved_timesteps", sa.Integer(), nullable=False),
        sa.Column("training_status", sa.String(length=40), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("stopped_early", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("resume_mode", sa.String(length=80), nullable=False),
        sa.Column("resume_source", sa.Text(), nullable=True),
        sa.Column("resume_saved_timesteps", sa.Integer(), nullable=True),
        sa.Column("evaluation_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mean_reward", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("local_run_dir", sa.Text(), nullable=False),
        sa.Column("local_report_path", sa.Text(), nullable=False),
        sa.Column(
            "sync_status",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'local_only'"),
        ),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "training_status IN ('completed', 'early_stopped', 'interrupted', "
            "'keyboard_interrupt', 'vizdoom_exit')",
            name=op.f("ck_training_runs_training_status"),
        ),
        sa.CheckConstraint(
            "sync_status IN ('local_only', 'pending', 'synced', 'failed')",
            name=op.f("ck_training_runs_sync_status"),
        ),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_training_runs")),
    )
    op.create_index(
        "ix_training_runs_scenario_created_at",
        "training_runs",
        ["scenario_key", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_training_runs_status_created_at",
        "training_runs",
        ["training_status", "created_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_training_runs_sync_status_created_at",
        "training_runs",
        ["sync_status", "created_at_utc"],
        unique=False,
    )

    op.create_table(
        "run_artifacts",
        sa.Column("artifact_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("artifact_type", sa.String(length=40), nullable=False),
        sa.Column("artifact_role", sa.String(length=40), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("storage_backend", sa.String(length=40), nullable=True),
        sa.Column("bucket_name", sa.String(length=120), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("remote_uri", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("step", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "sync_status",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("uploaded_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "artifact_type IN ('checkpoint', 'video', 'tensorboard', 'report')",
            name=op.f("ck_run_artifacts_artifact_type"),
        ),
        sa.CheckConstraint(
            "artifact_role IS NULL OR artifact_role IN ('final', 'best', 'auto', 'eval', 'summary')",
            name=op.f("ck_run_artifacts_artifact_role"),
        ),
        sa.CheckConstraint(
            "sync_status IN ('local_only', 'pending', 'synced', 'failed')",
            name=op.f("ck_run_artifacts_sync_status"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["training_runs.run_id"],
            name=op.f("fk_run_artifacts_run_id_training_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("artifact_id", name=op.f("pk_run_artifacts")),
        sa.UniqueConstraint("remote_uri", name="uq_run_artifacts_remote_uri"),
    )
    op.create_index("ix_run_artifacts_run_type", "run_artifacts", ["run_id", "artifact_type"])
    op.create_index("ix_run_artifacts_sync_status", "run_artifacts", ["sync_status"])

    op.create_table(
        "sync_events",
        sa.Column("event_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("artifact_id", sa.BigInteger(), nullable=True),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "operation IN ('upload', 'download', 'verify', 'resync')",
            name=op.f("ck_sync_events_operation"),
        ),
        sa.CheckConstraint(
            "status IN ('started', 'succeeded', 'failed')",
            name=op.f("ck_sync_events_status"),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["run_artifacts.artifact_id"],
            name=op.f("fk_sync_events_artifact_id_run_artifacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["training_runs.run_id"],
            name=op.f("fk_sync_events_run_id_training_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_sync_events")),
    )
    op.create_index("ix_sync_events_artifact_started_at", "sync_events", ["artifact_id", "started_at"])
    op.create_index("ix_sync_events_run_started_at", "sync_events", ["run_id", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_sync_events_run_started_at", table_name="sync_events")
    op.drop_index("ix_sync_events_artifact_started_at", table_name="sync_events")
    op.drop_table("sync_events")
    op.drop_index("ix_run_artifacts_sync_status", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_run_type", table_name="run_artifacts")
    op.drop_table("run_artifacts")
    op.drop_index("ix_training_runs_sync_status_created_at", table_name="training_runs")
    op.drop_index("ix_training_runs_status_created_at", table_name="training_runs")
    op.drop_index("ix_training_runs_scenario_created_at", table_name="training_runs")
    op.drop_table("training_runs")
