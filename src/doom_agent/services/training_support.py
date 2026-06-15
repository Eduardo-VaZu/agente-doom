from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import VecEnv

from doom_agent.config.schema import TrainingProfile
from doom_agent.models import build_recurrent_ppo_model
from doom_agent.services.early_stopping import EarlyStoppingTracker
from doom_agent.services.resume import ResumeState
from doom_agent.shared.contracts import EvaluationMetricsPayload
from doom_agent.utils.checkpoints import (
    build_checkpoint_metadata,
    checkpoint_zip_path,
    load_checkpoint_metadata,
    save_checkpoint_bundle,
)
from doom_agent.utils.console import print_block, print_kv_block
from doom_agent.utils.formatting import format_path_tail


@dataclass(frozen=True, slots=True)
class EvaluationSettings:
    frequency: int
    episodes: int
    save_best: bool
    best_checkpoint_stem: Path


def _next_multiple(current_timesteps: int, frequency: int) -> int:
    return ((current_timesteps // frequency) + 1) * frequency


def load_training_model(
    env: VecEnv,
    profile: TrainingProfile,
    tensorboard_dir: Path,
    resume_state: ResumeState,
) -> RecurrentPPO:
    if not resume_state.is_resumed:
        return build_recurrent_ppo_model(env, profile, str(tensorboard_dir))

    assert resume_state.checkpoint is not None
    model = RecurrentPPO.load(
        str(checkpoint_zip_path(resume_state.checkpoint.checkpoint_stem)),
        env=env,
    )
    model.set_random_seed(profile.seed)
    model.tensorboard_log = str(tensorboard_dir)
    return model


def load_best_mean_reward(best_checkpoint_stem: Path) -> float:
    metadata = load_checkpoint_metadata(best_checkpoint_stem)
    if metadata is None:
        return float("-inf")

    evaluation_metrics = metadata["evaluation_metrics"]
    if evaluation_metrics is None:
        return float("-inf")

    return float(evaluation_metrics["mean_reward"])


class PeriodicTrainingCallback(BaseCallback):
    def __init__(
        self,
        *,
        profile_name: str,
        profile: TrainingProfile,
        auto_checkpoint_dir: Path,
        evaluation_settings: EvaluationSettings,
        eval_env: VecEnv,
        resume_state: ResumeState,
        verbose: int = 0,
    ) -> None:
        super().__init__(verbose=verbose)
        self.profile_name = profile_name
        self.profile = profile
        self.auto_checkpoint_dir = auto_checkpoint_dir
        self.evaluation_settings = evaluation_settings
        self.eval_env = eval_env
        self.resume_state = resume_state
        self.next_checkpoint_step = profile.checkpoint_frequency
        self.next_eval_step = evaluation_settings.frequency
        self.best_mean_reward = load_best_mean_reward(evaluation_settings.best_checkpoint_stem)
        self.early_stopping = EarlyStoppingTracker(
            config=profile.early_stopping,
            best_mean_reward=self.best_mean_reward,
        )
        self.last_evaluation_metrics: EvaluationMetricsPayload | None = None
        self.action_counts: Counter[int] = Counter()
        self.action_labels: tuple[str, ...] = ()

    def _on_training_start(self) -> None:
        current_timesteps = self.model.num_timesteps
        self.next_checkpoint_step = _next_multiple(
            current_timesteps, self.profile.checkpoint_frequency
        )
        self.next_eval_step = _next_multiple(current_timesteps, self.evaluation_settings.frequency)
        self.action_labels = self._load_action_labels()

    def _on_step(self) -> bool:
        self._record_actions()
        if self.num_timesteps >= self.next_eval_step:
            self._run_periodic_evaluation()
            if self.early_stopping.stopped:
                return False
            self.next_eval_step += self.evaluation_settings.frequency

        if self.num_timesteps >= self.next_checkpoint_step:
            self._save_periodic_checkpoint()
            self.next_checkpoint_step += self.profile.checkpoint_frequency
        return True

    def _on_training_end(self) -> None:
        self.eval_env.close()

    def _run_periodic_evaluation(self) -> None:
        rewards, lengths = cast(
            tuple[list[float], list[int]],
            evaluate_policy(
                self.model,
                self.eval_env,
                n_eval_episodes=self.evaluation_settings.episodes,
                deterministic=True,
                return_episode_rewards=True,
                warn=False,
            ),
        )
        mean_reward = float(np.mean(rewards))
        std_reward = float(np.std(rewards))
        mean_length = float(np.mean(lengths))
        self.last_evaluation_metrics = {
            "mean_reward": mean_reward,
            "std_reward": std_reward,
            "mean_episode_length": mean_length,
            "episodes": self.evaluation_settings.episodes,
        }
        self.logger.record("eval/mean_reward", mean_reward)
        self.logger.record("eval/std_reward", std_reward)
        self.logger.record("eval/mean_episode_length", mean_length)

        if self.verbose:
            print_kv_block(
                "Evaluation",
                [
                    ("step", self.num_timesteps),
                    ("mean_reward", mean_reward),
                    ("std_reward", std_reward),
                    ("mean_length", mean_length),
                    ("episodes", self.evaluation_settings.episodes),
                    ("best_reward", self.best_mean_reward),
                ],
            )
        self._print_action_usage()

        improved = self.early_stopping.register(mean_reward)
        self.best_mean_reward = self.early_stopping.best_mean_reward

        if self.verbose and self.early_stopping.stopped and self.early_stopping.stop_reason:
            print_block("Early Stopping", [self.early_stopping.stop_reason])

        if self.evaluation_settings.save_best and improved:
            self.best_mean_reward = mean_reward
            metadata = build_checkpoint_metadata(
                profile_name=self.profile_name,
                profile=self.profile,
                saved_timesteps=self.num_timesteps,
                resume_source=self.resume_state.resume_source,
                resume_saved_timesteps=self.resume_state.resume_saved_timesteps,
                training_status="best_model",
                evaluation_metrics=self.last_evaluation_metrics,
                is_best_checkpoint=True,
            )
            save_checkpoint_bundle(
                self.model,
                self.evaluation_settings.best_checkpoint_stem,
                metadata,
            )
            if self.verbose:
                print_kv_block(
                    "Best Model",
                    [
                        ("step", self.num_timesteps),
                        (
                            "path",
                            format_path_tail(
                                self.evaluation_settings.best_checkpoint_stem.with_suffix(".zip")
                            ),
                        ),
                    ],
                )

    def _save_periodic_checkpoint(self) -> None:
        checkpoint_stem = self.auto_checkpoint_dir / (
            f"{self.profile.checkpoint_name}_{self.num_timesteps}_steps"
        )
        metadata = build_checkpoint_metadata(
            profile_name=self.profile_name,
            profile=self.profile,
            saved_timesteps=self.num_timesteps,
            resume_source=self.resume_state.resume_source,
            resume_saved_timesteps=self.resume_state.resume_saved_timesteps,
            training_status="periodic_checkpoint",
            evaluation_metrics=self.last_evaluation_metrics,
        )
        save_checkpoint_bundle(self.model, checkpoint_stem, metadata)
        if self.verbose:
            print_kv_block(
                "Checkpoint",
                [
                    ("step", self.num_timesteps),
                    ("path", format_path_tail(checkpoint_stem.with_suffix(".zip"))),
                ],
            )
        self._print_action_usage()

    def _load_action_labels(self) -> tuple[str, ...]:
        if self.profile.action_space_kind != "button_combinations":
            return ()

        labels_by_env = self.training_env.get_attr("action_labels")
        if not labels_by_env:
            return ()

        labels = labels_by_env[0]
        if not isinstance(labels, tuple):
            return ()
        return tuple(str(label) for label in labels)

    def _record_actions(self) -> None:
        if self.profile.action_space_kind != "button_combinations":
            return

        actions = self.locals.get("actions")
        if actions is None:
            return

        for action_index in np.asarray(actions).reshape(-1):
            self.action_counts[int(action_index)] += 1

    def _print_action_usage(self) -> None:
        if not self.verbose or not self.action_counts:
            return

        total = sum(self.action_counts.values())
        top_actions = []
        for action_index, count in self.action_counts.most_common(5):
            label = (
                self.action_labels[action_index]
                if 0 <= action_index < len(self.action_labels)
                else str(action_index)
            )
            percentage = (count / total) * 100
            top_actions.append(f"{label}={count} ({percentage:.1f}%)")

        print_block("Recent Actions", top_actions)
        self.action_counts.clear()
