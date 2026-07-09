from __future__ import annotations

from typing import Literal, Protocol, TypeAlias, TypedDict


class RewardShapingPayload(TypedDict, total=False):
    scale: float
    offset: float
    clip_min: float | None
    clip_max: float | None


class EarlyStoppingPayload(TypedDict, total=False):
    enabled: bool
    patience_evaluations: int
    min_evaluations: int
    min_delta: float


class CurriculumStagePayload(TypedDict, total=False):
    scenario_key: str
    requested_timesteps: int | None


class TrainingProfilePayload(TypedDict, total=False):
    scenario_name: str
    learning_rate: float
    n_steps: int
    batch_size: int
    n_epochs: int
    gamma: float
    gae_lambda: float
    ent_coef: float
    requested_timesteps: int
    render: bool
    record_video: bool
    checkpoint_name: str
    tensorboard_run_name: str
    checkpoint_frequency: int
    eval_frequency: int
    eval_episodes: int
    video_record_frequency: int
    video_length: int
    frame_stack: int
    screen_width: int
    screen_height: int
    observation_mode: str
    seed: int
    action_space_kind: str
    action_combo_preset: str
    scenario_key: str
    scenario_description: str
    reward_shaping: RewardShapingPayload
    early_stopping: EarlyStoppingPayload
    curriculum: list[CurriculumStagePayload]
    effective_timesteps: int
    uses_rounded_timesteps: bool


class EvaluationMetricsPayload(TypedDict):
    mean_reward: float
    std_reward: float
    mean_episode_length: float
    episodes: int


class EvaluationActionUsagePayload(TypedDict):
    label: str
    count: int
    percentage: float


class EvaluationHistoryEntryPayload(TypedDict):
    step: int
    mean_reward: float
    std_reward: float
    mean_episode_length: float
    episodes: int
    top_actions: list[EvaluationActionUsagePayload]


class EvaluationSummaryPayload(TypedDict):
    checkpoint_path: str
    scenario_key: str
    scenario_name: str
    deterministic: bool
    render: bool
    metrics: EvaluationMetricsPayload


class WorkspaceCheckpointPointerPayload(TypedDict):
    profile_name: str
    scenario_key: str
    run_id: str
    source_checkpoint_role: str | None
    source_relative_run_path: str | None
    report_relative_run_path: str
    saved_timesteps: int
    evaluation_metrics: EvaluationMetricsPayload | None
    updated_at_utc: str


class WorkspaceCheckpointLinePayload(TypedDict, total=False):
    active: WorkspaceCheckpointPointerPayload
    promoted: WorkspaceCheckpointPointerPayload


class WorkspaceStatePayload(TypedDict):
    updated_at_utc: str
    checkpoint_lines: dict[str, WorkspaceCheckpointLinePayload]


class RunManifestArtifactPayload(TypedDict, total=False):
    relative_path: str
    artifact_type: str
    artifact_role: str | None
    sidecar_kind: str | None
    remote_sync_candidate: bool
    exists: bool
    file_size_bytes: int | None


class RunManifestPayload(TypedDict):
    manifest_version: int
    run_id: str
    created_at_utc: str
    profile_name: str
    run_label: str | None
    profile: TrainingProfilePayload
    scenario_key: str
    scenario_name: str
    checkpoint_name: str
    seed: int
    requested_timesteps: int
    effective_timesteps: int
    saved_timesteps: int
    training_status: str
    completed: bool
    evaluation_metrics: EvaluationMetricsPayload | None
    artifacts: list[RunManifestArtifactPayload]


class RunInspectionPayload(TypedDict):
    run_id: str
    created_at_utc: str
    profile_name: str
    run_label: str | None
    scenario_key: str
    scenario_name: str
    checkpoint_name: str
    seed: int
    requested_timesteps: int
    effective_timesteps: int
    saved_timesteps: int
    training_status: str
    completed: bool
    sync_status: str | None
    mean_reward: float | None
    std_reward: float | None
    mean_episode_length: float | None
    evaluation_episodes: int | None
    evaluation_history_count: int
    latest_evaluation_step: int | None
    report_path: str
    report_exists: bool
    manifest_path: str
    manifest_exists: bool
    checkpoint_archive_path: str
    checkpoint_archive_exists: bool
    best_checkpoint_archive_path: str | None
    best_checkpoint_archive_exists: bool
    selected_auto_checkpoint_archive_paths: list[str]
    selected_auto_checkpoint_count: int
    remote_sync_candidates: list[str]
    remote_sync_candidate_count: int
    handoff_ready: bool


class CheckpointMetadataPayload(TypedDict):
    profile_name: str
    run_id: str | None
    saved_timesteps: int
    saved_at_utc: str
    profile: TrainingProfilePayload
    resume_source: str | None
    resume_saved_timesteps: int | None
    training_status: str | None
    checkpoint_role: str | None
    evaluation_source: str | None
    canonical_checkpoint_path: str | None
    evaluation_metrics: EvaluationMetricsPayload | None
    is_best_checkpoint: bool


class TrainingRunReportPayload(TypedDict):
    run_id: str
    created_at_utc: str
    profile_name: str
    run_label: str | None
    profile: TrainingProfilePayload
    scenario_key: str
    scenario_name: str
    checkpoint_name: str
    checkpoint_path: str
    best_checkpoint_path: str | None
    official_checkpoint_path: str | None
    official_best_checkpoint_path: str | None
    manifest_path: str
    checkpoint_archive_path: str
    best_checkpoint_archive_path: str | None
    selected_auto_checkpoint_archive_paths: list[str]
    run_dir: str
    run_auto_checkpoints_dir: str
    tensorboard_dir: str
    videos_dir: str
    training_status: str
    completed: bool
    requested_timesteps: int
    effective_timesteps: int
    saved_timesteps: int
    seed: int
    resume_mode: str
    resume_source: str | None
    resume_saved_timesteps: int | None
    evaluation_metrics: EvaluationMetricsPayload | None
    evaluation_history: list[EvaluationHistoryEntryPayload]
    duration_seconds: float
    stopped_early: bool
    stop_reason: str | None


class ExperimentIndexEntryPayload(TypedDict):
    run_id: str
    created_at_utc: str
    profile_name: str
    run_label: str | None
    scenario_key: str
    checkpoint_name: str
    checkpoint_path: str
    best_checkpoint_path: str | None
    checkpoint_archive_path: str
    best_checkpoint_archive_path: str | None
    saved_timesteps: int
    training_status: str
    mean_reward: float | None
    seed: int
    report_path: str


class ExperimentIndexPayload(TypedDict):
    runs: list[ExperimentIndexEntryPayload]


class LegacyConfigPayload(TypedDict, total=False):
    env_name: str
    learning_rate: float
    n_steps: int
    batch_size: int
    n_epochs: int
    gamma: float
    gae_lambda: float
    ent_coef: float
    total_timesteps: int
    requested_timesteps: int
    effective_timesteps: int
    render: bool
    record: bool
    save_name: str
    tb_log_name: str
    checkpoint_freq: int
    eval_frequency: int
    eval_episodes: int
    video_record_frequency: int
    video_length: int
    frame_stack: int
    screen_width: int
    screen_height: int
    observation_mode: str
    seed: int
    scenario_key: str
    scenario_description: str
    action_combo_preset: str
    reward_shaping: RewardShapingPayload
    early_stopping: EarlyStoppingPayload
    curriculum: list[CurriculumStagePayload]
    LOG_DIR: str
    SCENARIOS_DIR: str
    VIDEO_DIR: str


class SaveableModel(Protocol):
    def save(self, path: str) -> None: ...


ProfileOverrides: TypeAlias = dict[str, object]
ScenarioOverrides: TypeAlias = dict[str, object]
CatalogSection: TypeAlias = dict[str, ProfileOverrides]
CheckpointSelection: TypeAlias = Literal["best", "last", "exact"]
