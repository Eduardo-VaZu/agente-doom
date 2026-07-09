from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doom_agent.config.schema import ProjectPaths, TrainingProfile
from doom_agent.utils.checkpoints import (
    ResolvedCheckpoint,
    checkpoint_zip_path,
    resolve_checkpoint,
    resolve_resume_checkpoint,
)

AUTO_RESUME_MODE = "auto"
LATEST_RESUME_MODE = "latest"


@dataclass(frozen=True, slots=True)
class ResumeState:
    mode: str
    checkpoint: ResolvedCheckpoint | None
    note: str | None = None

    @property
    def is_resumed(self) -> bool:
        return self.checkpoint is not None

    @property
    def resume_source(self) -> str | None:
        if self.checkpoint is None:
            return None
        return str(checkpoint_zip_path(self.checkpoint.checkpoint_stem))

    @property
    def resume_saved_timesteps(self) -> int | None:
        if self.checkpoint is None:
            return None
        return self.checkpoint.saved_timesteps


def _action_space_kind(action_space: Any) -> str:
    import gymnasium as gym

    if isinstance(action_space, gym.spaces.Discrete):
        return "discrete"
    if isinstance(action_space, gym.spaces.MultiDiscrete):
        return "multidiscrete"
    raise ValueError(f"Action space no soportado para reanudacion: {action_space}")


def _legacy_compatibility_issues(profile: TrainingProfile, checkpoint_stem: Path) -> list[str]:
    from sb3_contrib import RecurrentPPO

    legacy_model = RecurrentPPO.load(str(checkpoint_zip_path(checkpoint_stem)))
    observation_shape = legacy_model.observation_space.shape
    issues: list[str] = []

    if observation_shape != (
        profile.stacked_observation_channels,
        profile.screen_height,
        profile.screen_width,
    ):
        issues.append(
            "La forma de observacion del checkpoint legacy "
            f"{observation_shape} no coincide con {(profile.stacked_observation_channels, profile.screen_height, profile.screen_width)}."
        )

    checkpoint_action_space_kind = _action_space_kind(legacy_model.action_space)
    if checkpoint_action_space_kind != profile.action_space_kind:
        issues.append(
            f"El action space del checkpoint legacy ({checkpoint_action_space_kind}) "
            f"no coincide con el actual ({profile.action_space_kind})."
        )
    return issues


def resolve_resume_state(
    project_paths: ProjectPaths,
    profile: TrainingProfile,
    *,
    resume_mode: str = AUTO_RESUME_MODE,
    from_scratch: bool = False,
    allow_scenario_change: bool = False,
) -> ResumeState:
    if from_scratch:
        return ResumeState(mode="from_scratch", checkpoint=None)

    if resume_mode in {AUTO_RESUME_MODE, LATEST_RESUME_MODE}:
        checkpoint = resolve_resume_checkpoint(project_paths, profile.checkpoint_name)
        if checkpoint is None:
            return ResumeState(mode=resume_mode, checkpoint=None)
    else:
        checkpoint = resolve_checkpoint(project_paths, resume_mode)

    if checkpoint.metadata is None:
        issues = _legacy_compatibility_issues(profile, checkpoint.checkpoint_stem)
        if issues:
            formatted_issues = "\n".join(f"- {issue}" for issue in issues)
            raise ValueError(
                "El checkpoint legacy no es compatible con el entrenamiento actual:\n"
                f"{formatted_issues}"
            )
        note = (
            "Checkpoint legacy sin metadata completa. Se valido observation/action space, "
            "pero no fue posible comparar todos los hiperparametros."
        )
        return ResumeState(mode=resume_mode, checkpoint=checkpoint, note=note)

    previous_profile = TrainingProfile.from_dict(checkpoint.metadata["profile"])
    if allow_scenario_change:
        issues = profile.model_compatibility_issues(previous_profile)
    else:
        issues = profile.resume_compatibility_issues(previous_profile)
    if issues:
        formatted_issues = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(
            "El checkpoint encontrado no es compatible con la configuracion actual. "
            "Usa '--from-scratch' o ajusta la configuracion.\n"
            f"{formatted_issues}"
        )

    return ResumeState(mode=resume_mode, checkpoint=checkpoint)
