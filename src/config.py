"""Backward-compatible config exports.

Public flow keeps only ``CONFIG`` as normal training preset.
Additional presets remain available only for legacy/internal compatibility.
"""

from doom_agent.config import SCENARIO_NAMES, TRAINING_PROFILES, build_project_paths
from doom_agent.config.schema import TrainingProfile
from doom_agent.shared.contracts import LegacyConfigPayload

PROJECT_PATHS = build_project_paths()
BASE_DIR = str(PROJECT_PATHS.root_dir)
SCENARIOS_DIR = str(PROJECT_PATHS.scenarios_dir)
LOG_DIR = str(PROJECT_PATHS.artifacts_dir)
VIDEO_DIR = str(PROJECT_PATHS.videos_dir)


def _profile_to_legacy_config(profile: TrainingProfile) -> LegacyConfigPayload:
    return {
        "env_name": profile.scenario_name,
        "learning_rate": profile.learning_rate,
        "n_steps": profile.n_steps,
        "batch_size": profile.batch_size,
        "n_epochs": profile.n_epochs,
        "gamma": profile.gamma,
        "gae_lambda": profile.gae_lambda,
        "ent_coef": profile.ent_coef,
        "total_timesteps": profile.requested_timesteps,
        "effective_timesteps": profile.effective_timesteps,
        "render": profile.render,
        "record": profile.record_video,
        "save_name": profile.checkpoint_name,
        "tb_log_name": profile.tensorboard_run_name,
        "checkpoint_freq": profile.checkpoint_frequency,
        "video_record_frequency": profile.video_record_frequency,
        "video_length": profile.video_length,
        "frame_stack": profile.frame_stack,
        "screen_width": profile.screen_width,
        "screen_height": profile.screen_height,
        "seed": profile.seed,
        "action_combo_preset": profile.action_combo_preset,
        "scenario_key": profile.scenario_key,
        "scenario_description": profile.scenario_description,
        "reward_shaping": profile.reward_shaping.to_dict(),
        "early_stopping": profile.early_stopping.to_dict(),
        "curriculum": [stage.to_dict() for stage in profile.curriculum],
    }


CONFIG = _profile_to_legacy_config(TRAINING_PROFILES["default"])

TRAINING_CONFIGS: dict[str, LegacyConfigPayload] = {
    "default": CONFIG,
}

INTERNAL_TRAINING_CONFIGS: dict[str, LegacyConfigPayload] = {}

__all__ = [
    "BASE_DIR",
    "SCENARIOS_DIR",
    "LOG_DIR",
    "VIDEO_DIR",
    "SCENARIO_NAMES",
    "CONFIG",
    "INTERNAL_TRAINING_CONFIGS",
    "TRAINING_CONFIGS",
]
