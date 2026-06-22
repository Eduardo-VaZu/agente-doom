from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import VecEnv

from doom_agent.config.schema import TrainingProfile
from doom_agent.models import build_recurrent_ppo_model
from doom_agent.services.early_stopping import EarlyStoppingTracker
from doom_agent.services.resume import ResumeState
from doom_agent.shared.contracts import (
    EvaluationActionUsagePayload,
    EvaluationHistoryEntryPayload,
    EvaluationMetricsPayload,
)
from doom_agent.utils.checkpoints import (
    build_checkpoint_metadata,
    checkpoint_zip_path,
    copy_checkpoint_bundle,
    load_checkpoint_metadata,
    save_checkpoint_bundle,
)
from doom_agent.utils.console import print_block, print_kv_block
from doom_agent.utils.formatting import format_path_tail

if TYPE_CHECKING:
    from doom_agent.utils.checkpoints import ResolvedCheckpoint


@dataclass(frozen=True, slots=True)
class EvaluationSettings:
    frequency: int
    episodes: int
    save_best: bool
    best_checkpoint_stem: Path
    compatibility_best_checkpoint_stem: Path | None
    seed: int


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


def _mean_reward_from_metrics(
    evaluation_metrics: EvaluationMetricsPayload | None,
) -> float | None:
    if evaluation_metrics is None:
        return None
    return float(evaluation_metrics["mean_reward"])


def load_best_mean_reward(
    best_checkpoint_stem: Path,
    *,
    resume_checkpoint: ResolvedCheckpoint | None = None,
) -> float:
    metadata = load_checkpoint_metadata(best_checkpoint_stem)
    if metadata is None:
        if resume_checkpoint is None or resume_checkpoint.metadata is None:
            return float("-inf")
        resume_mean_reward = _mean_reward_from_metrics(
            resume_checkpoint.metadata["evaluation_metrics"]
        )
        if resume_mean_reward is None:
            return float("-inf")
        return resume_mean_reward

    mean_reward = _mean_reward_from_metrics(metadata["evaluation_metrics"])
    if mean_reward is None:
        return float("-inf")

    return mean_reward


def build_evaluation_metrics(
    rewards: list[float],
    lengths: list[int],
    *,
    episodes: int,
) -> EvaluationMetricsPayload:
    return {
        "mean_reward": float(np.mean(rewards)),
        "std_reward": float(np.std(rewards)),
        "mean_episode_length": float(np.mean(lengths)),
        "episodes": episodes,
    }


def summarize_action_usage(
    action_counts: Counter[int],
    action_labels: tuple[str, ...],
    *,
    limit: int = 5,
) -> list[EvaluationActionUsagePayload]:
    total = sum(action_counts.values())
    if total <= 0:
        return []

    top_actions: list[EvaluationActionUsagePayload] = []
    for action_index, count in action_counts.most_common(limit):
        label = (
            action_labels[action_index]
            if 0 <= action_index < len(action_labels)
            else str(action_index)
        )
        top_actions.append(
            {
                "label": label,
                "count": count,
                "percentage": (count / total) * 100,
            }
        )
    return top_actions


def _sanitize_metric_label(label: str) -> str:
    sanitized = "".join(character.lower() if character.isalnum() else "_" for character in label)
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized.strip("_") or "unknown"


class PeriodicTrainingCallback(BaseCallback):
    def __init__(
        self,
        *,
        run_id: str,
        profile_name: str,
        profile: TrainingProfile,
        auto_checkpoint_dir: Path,
        compatibility_auto_checkpoint_dir: Path | None,
        evaluation_settings: EvaluationSettings,
        eval_env: VecEnv,
        resume_state: ResumeState,
        verbose: int = 0,
    ) -> None:
        super().__init__(verbose=verbose)
        self.run_id = run_id
        self.profile_name = profile_name
        self.profile = profile
        self.auto_checkpoint_dir = auto_checkpoint_dir
        self.compatibility_auto_checkpoint_dir = compatibility_auto_checkpoint_dir
        self.evaluation_settings = evaluation_settings
        self.eval_env = eval_env
        self.resume_state = resume_state
        self.next_checkpoint_step = profile.checkpoint_frequency
        self.next_eval_step = evaluation_settings.frequency
        self.best_mean_reward = load_best_mean_reward(
            evaluation_settings.best_checkpoint_stem,
            resume_checkpoint=resume_state.checkpoint,
        )
        self.early_stopping = EarlyStoppingTracker(
            config=profile.early_stopping,
            best_mean_reward=self.best_mean_reward,
        )
        self.best_checkpoint_updated = False
        self.last_evaluation_metrics: EvaluationMetricsPayload | None = None
        self.evaluation_history: list[EvaluationHistoryEntryPayload] = []
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
        self.eval_env.seed(self.evaluation_settings.seed)
        previous_best_mean_reward = self.best_mean_reward
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
        self.last_evaluation_metrics = build_evaluation_metrics(
            rewards,
            lengths,
            episodes=self.evaluation_settings.episodes,
        )
        mean_reward = self.last_evaluation_metrics["mean_reward"]
        std_reward = self.last_evaluation_metrics["std_reward"]
        mean_length = self.last_evaluation_metrics["mean_episode_length"]
        previous_best_for_logging = (
            previous_best_mean_reward if np.isfinite(previous_best_mean_reward) else mean_reward
        )
        action_usage = self._consume_action_usage()
        self.evaluation_history.append(
            {
                "step": self.num_timesteps,
                "mean_reward": mean_reward,
                "std_reward": std_reward,
                "mean_episode_length": mean_length,
                "episodes": self.evaluation_settings.episodes,
                "top_actions": action_usage,
            }
        )
        self.logger.record("eval/mean_reward", mean_reward)
        self.logger.record("eval/std_reward", std_reward)
        self.logger.record("eval/mean_episode_length", mean_length)
        self.logger.record("eval/episodes", self.evaluation_settings.episodes)
        self.logger.record("eval/best_mean_reward_so_far", previous_best_for_logging)
        self.logger.record("eval/reward_gap_vs_best", mean_reward - previous_best_for_logging)
        self.logger.record("eval/evaluation_index", len(self.evaluation_history))
        self._record_action_usage_metrics(action_usage)

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
        self._print_action_usage(action_usage)

        improved = self.early_stopping.register(mean_reward)
        self.best_mean_reward = self.early_stopping.best_mean_reward
        self.logger.record("eval/is_new_best", 1.0 if improved else 0.0)

        if self.verbose and self.early_stopping.stopped and self.early_stopping.stop_reason:
            print_block("Early Stopping", [self.early_stopping.stop_reason])

        if self.evaluation_settings.save_best and improved:
            self.best_mean_reward = mean_reward
            self.best_checkpoint_updated = True
            metadata = build_checkpoint_metadata(
                profile_name=self.profile_name,
                profile=self.profile,
                saved_timesteps=self.num_timesteps,
                run_id=self.run_id,
                resume_source=self.resume_state.resume_source,
                resume_saved_timesteps=self.resume_state.resume_saved_timesteps,
                training_status="best_model",
                checkpoint_role="best",
                evaluation_source="training_internal",
                canonical_checkpoint_path=str(
                    self.evaluation_settings.best_checkpoint_stem.with_suffix(".zip")
                ),
                evaluation_metrics=self.last_evaluation_metrics,
                is_best_checkpoint=True,
            )
            save_checkpoint_bundle(
                self.model,
                self.evaluation_settings.best_checkpoint_stem,
                metadata,
            )
            if self.evaluation_settings.compatibility_best_checkpoint_stem is not None:
                copy_checkpoint_bundle(
                    self.evaluation_settings.best_checkpoint_stem,
                    self.evaluation_settings.compatibility_best_checkpoint_stem,
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
            run_id=self.run_id,
            resume_source=self.resume_state.resume_source,
            resume_saved_timesteps=self.resume_state.resume_saved_timesteps,
            training_status="periodic_checkpoint",
            checkpoint_role="auto",
            evaluation_source="training_internal",
            canonical_checkpoint_path=str(checkpoint_stem.with_suffix(".zip")),
            evaluation_metrics=self.last_evaluation_metrics,
        )
        save_checkpoint_bundle(self.model, checkpoint_stem, metadata)
        if self.compatibility_auto_checkpoint_dir is not None:
            copy_checkpoint_bundle(
                checkpoint_stem,
                self.compatibility_auto_checkpoint_dir / checkpoint_stem.name,
            )
        if self.verbose:
            print_kv_block(
                "Checkpoint",
                [
                    ("step", self.num_timesteps),
                    ("path", format_path_tail(checkpoint_stem.with_suffix(".zip"))),
                ],
            )

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

    def _consume_action_usage(self) -> list[EvaluationActionUsagePayload]:
        action_usage = summarize_action_usage(self.action_counts, self.action_labels)
        self.action_counts.clear()
        return action_usage

    def _print_action_usage(self, action_usage: list[EvaluationActionUsagePayload]) -> None:
        if not self.verbose or not action_usage:
            return

        print_block(
            "Recent Actions",
            [
                f"{entry['label']}={entry['count']} ({entry['percentage']:.1f}%)"
                for entry in action_usage
            ],
        )

    def _record_action_usage_metrics(
        self,
        action_usage: list[EvaluationActionUsagePayload],
    ) -> None:
        if not action_usage:
            self.logger.record("eval/actions/unique_top_actions", 0)
            self.logger.record("eval/actions/dominant_action_percentage", 0.0)
            return

        self.logger.record("eval/actions/unique_top_actions", len(action_usage))
        self.logger.record("eval/actions/dominant_action_percentage", action_usage[0]["percentage"])

        for entry in action_usage:
            sanitized_label = _sanitize_metric_label(entry["label"])
            self.logger.record(
                f"eval/actions/{sanitized_label}_percentage",
                entry["percentage"],
            )
            self.logger.record(
                f"eval/actions/{sanitized_label}_count",
                entry["count"],
            )
