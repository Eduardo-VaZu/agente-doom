from __future__ import annotations

from enum import StrEnum


class SyncStatus(StrEnum):
    LOCAL_ONLY = "local_only"
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


class TrainingStatus(StrEnum):
    COMPLETED = "completed"
    EARLY_STOPPED = "early_stopped"
    INTERRUPTED = "interrupted"
    KEYBOARD_INTERRUPT = "keyboard_interrupt"
    VIZDOOM_EXIT = "vizdoom_exit"


class ArtifactType(StrEnum):
    CHECKPOINT = "checkpoint"
    VIDEO = "video"
    TENSORBOARD = "tensorboard"
    REPORT = "report"


class ArtifactRole(StrEnum):
    FINAL = "final"
    BEST = "best"
    AUTO = "auto"
    EVAL = "eval"
    SUMMARY = "summary"


class SyncOperation(StrEnum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    VERIFY = "verify"
    RESYNC = "resync"


class SyncEventStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
