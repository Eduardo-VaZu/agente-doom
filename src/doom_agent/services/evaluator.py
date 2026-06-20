from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import gymnasium as gym
import numpy as np
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.evaluation import evaluate_policy
from vizdoom import ViZDoomUnexpectedExitException

from doom_agent.config import (
    DEFAULT_PROFILE_NAME,
    build_project_paths,
    get_training_profile,
    override_profile_scenario,
)
from doom_agent.config.schema import TrainingProfile
from doom_agent.envs import make_vectorized_env
from doom_agent.services.training_support import build_evaluation_metrics
from doom_agent.shared.contracts import (
    CheckpointSelection,
    EvaluationSummaryPayload,
)
from doom_agent.utils.checkpoints import (
    checkpoint_zip_path,
    load_checkpoint_metadata,
    resolve_checkpoint_preference,
)
from doom_agent.utils.console import print_kv_block


def infer_legacy_profile(checkpoint_stem: Path) -> TrainingProfile:
    model = RecurrentPPO.load(str(checkpoint_zip_path(checkpoint_stem)))
    action_space = model.action_space
    base_profile = get_training_profile(DEFAULT_PROFILE_NAME).for_evaluation()

    if isinstance(action_space, gym.spaces.Discrete):
        return replace(base_profile, action_space_kind="discrete")

    if isinstance(action_space, gym.spaces.MultiDiscrete):
        return replace(base_profile, action_space_kind="multidiscrete")

    raise ValueError(f"No se pudo inferir un action space compatible: {action_space}")


def resolve_profile_for_evaluation(
    checkpoint_name: str | None = None,
    profile_name: str = DEFAULT_PROFILE_NAME,
    checkpoint_selection: CheckpointSelection = "best",
    scenario_name: str | None = None,
) -> tuple[TrainingProfile, Path]:
    project_paths = build_project_paths()
    resolved_checkpoint_name = checkpoint_name
    if resolved_checkpoint_name is None:
        resolved_checkpoint_name = get_training_profile(
            profile_name,
            scenario_name=scenario_name,
        ).checkpoint_name

    resolved_checkpoint = resolve_checkpoint_preference(
        project_paths,
        resolved_checkpoint_name,
        preference=checkpoint_selection,
    )
    checkpoint_stem = resolved_checkpoint.checkpoint_stem
    metadata = (
        resolved_checkpoint.metadata
        if resolved_checkpoint.metadata is not None
        else load_checkpoint_metadata(checkpoint_stem)
    )
    if metadata is None:
        profile = infer_legacy_profile(checkpoint_stem)
        if scenario_name is not None:
            profile = override_profile_scenario(profile, scenario_name)
        print(
            "No se encontro metadata asociada al checkpoint. "
            "Se usara el escenario del perfil 'default' con el action space inferido del checkpoint."
        )
        return profile.for_evaluation(), checkpoint_stem

    profile = TrainingProfile.from_dict(metadata["profile"]).for_evaluation()
    if scenario_name is not None:
        profile = override_profile_scenario(profile, scenario_name).for_evaluation()
    return profile, checkpoint_stem


def evaluate(
    checkpoint_name: str | None = None,
    steps: int | None = None,
    episodes: int | None = None,
    profile_name: str = DEFAULT_PROFILE_NAME,
    checkpoint_selection: CheckpointSelection = "best",
    scenario_name: str | None = None,
    *,
    render: bool | None = None,
    json_output: bool = False,
) -> EvaluationSummaryPayload | None:
    if steps is not None and episodes is not None:
        raise ValueError("No puedes usar '--steps' y '--episodes' al mismo tiempo.")

    project_paths = build_project_paths()
    profile, resolved_checkpoint_stem = resolve_profile_for_evaluation(
        checkpoint_name,
        profile_name=profile_name,
        checkpoint_selection=checkpoint_selection,
        scenario_name=scenario_name,
    )
    if render is not None:
        profile = profile.for_evaluation(render=render)
    profile = profile.with_seed(profile.seed + 1)
    profile.validate(project_paths)

    env = make_vectorized_env(profile, project_paths)
    env.seed(profile.seed)
    model = RecurrentPPO.load(str(checkpoint_zip_path(resolved_checkpoint_stem)), env=env)

    if episodes is not None:
        if episodes <= 0:
            raise ValueError("'episodes' debe ser mayor que cero.")
        try:
            rewards, lengths = cast(
                tuple[list[float], list[int]],
                evaluate_policy(
                    model,
                    env,
                    n_eval_episodes=episodes,
                    deterministic=True,
                    return_episode_rewards=True,
                    warn=False,
                ),
            )
            metrics = build_evaluation_metrics(rewards, lengths, episodes=episodes)
            summary: EvaluationSummaryPayload = {
                "checkpoint_path": str(checkpoint_zip_path(resolved_checkpoint_stem)),
                "scenario_key": profile.scenario_key,
                "scenario_name": profile.scenario_name,
                "deterministic": True,
                "render": profile.render,
                "metrics": metrics,
            }
            if json_output:
                print(json.dumps(summary, indent=2, sort_keys=True))
            else:
                print_kv_block(
                    "Evaluation Summary",
                    [
                        ("checkpoint", summary["checkpoint_path"]),
                        ("scenario", f"{summary['scenario_name']} ({summary['scenario_key']})"),
                        ("episodes", metrics["episodes"]),
                        ("mean_reward", metrics["mean_reward"]),
                        ("std_reward", metrics["std_reward"]),
                        ("mean_episode_length", metrics["mean_episode_length"]),
                        ("deterministic", summary["deterministic"]),
                        ("render", summary["render"]),
                    ],
                )
            return summary
        finally:
            env.close()

    observation = cast(np.ndarray, env.reset())
    lstm_states = None
    episode_starts = np.ones((env.num_envs,), dtype=bool)

    print(f"Evaluando checkpoint: {checkpoint_zip_path(resolved_checkpoint_stem)}.")
    print(
        f"Escenario de evaluacion: {profile.scenario_name} "
        f"({profile.scenario_key}). Presiona Ctrl+C para salir."
    )
    try:
        step_count = 0
        while steps is None or step_count < steps:
            action, lstm_states = model.predict(
                observation,
                state=lstm_states,
                episode_start=episode_starts,
                deterministic=True,
            )
            step_result = env.step(action)
            observation = cast(np.ndarray, step_result[0])
            dones = step_result[2]
            episode_starts = dones
            if profile.render:
                env.render()
            step_count += 1
        print(f"Evaluacion completada: {step_count} pasos ejecutados.")
    except KeyboardInterrupt:
        print("Evaluacion detenida por el usuario.")
    except ViZDoomUnexpectedExitException:
        print("Evaluacion detenida: la ventana de ViZDoom fue cerrada.")
    finally:
        env.close()

    return None
