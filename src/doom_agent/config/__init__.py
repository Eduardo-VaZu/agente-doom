"""Configuration models and training catalog accessors."""

from doom_agent.config.profiles import (
    ADVANCED_PROFILE_NAMES,
    DEFAULT_PROFILE_NAME,
    DEFAULT_SCENARIO_NAME,
    PROFILE_NAMES,
    PUBLIC_PROFILE_NAMES,
    SCENARIO_NAMES,
    TRAINING_PROFILES,
    build_project_paths,
    get_training_profile,
    load_training_catalog,
    materialize_curriculum_profiles,
    override_profile_scenario,
)
from doom_agent.config.schema import (
    CurriculumStageConfig,
    EarlyStoppingConfig,
    ProjectPaths,
    RewardShapingConfig,
    TrainingProfile,
)

__all__ = [
    "ADVANCED_PROFILE_NAMES",
    "DEFAULT_PROFILE_NAME",
    "DEFAULT_SCENARIO_NAME",
    "CurriculumStageConfig",
    "EarlyStoppingConfig",
    "PROFILE_NAMES",
    "ProjectPaths",
    "PUBLIC_PROFILE_NAMES",
    "RewardShapingConfig",
    "SCENARIO_NAMES",
    "TRAINING_PROFILES",
    "TrainingProfile",
    "build_project_paths",
    "get_training_profile",
    "load_training_catalog",
    "materialize_curriculum_profiles",
    "override_profile_scenario",
]
