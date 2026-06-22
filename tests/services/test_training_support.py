from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path
from typing import cast
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from stable_baselines3.common.base_class import BaseAlgorithm
from stable_baselines3.common.vec_env import VecEnv

from doom_agent.config import get_training_profile
from doom_agent.config.schema import EarlyStoppingConfig
from doom_agent.services.early_stopping import EarlyStoppingTracker
from doom_agent.services.resume import ResumeState
from doom_agent.services.training_support import (
    EvaluationSettings,
    PeriodicTrainingCallback,
    summarize_action_usage,
)


class FakeVecEnv:
    def __init__(self) -> None:
        self.seed_calls: list[int] = []

    def seed(self, seed: int) -> None:
        self.seed_calls.append(seed)

    def close(self) -> None:
        return None


class FakeLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, float]] = []

    def record(self, _key: str, _value: float) -> None:
        self.records.append((_key, _value))


class FakeModel:
    def __init__(self) -> None:
        self.logger = FakeLogger()

    def save(self, checkpoint_stem: str) -> None:
        Path(checkpoint_stem).with_suffix(".zip").write_text("model", encoding="utf-8")


class EarlyStoppingTests(unittest.TestCase):
    def test_early_stopping_tracker_stops_after_patience(self) -> None:
        tracker = EarlyStoppingTracker(
            config=EarlyStoppingConfig(
                enabled=True,
                patience_evaluations=2,
                min_evaluations=2,
                min_delta=0.1,
            )
        )

        self.assertTrue(tracker.register(1.0))
        self.assertFalse(tracker.stopped)

        self.assertFalse(tracker.register(1.05))
        self.assertFalse(tracker.stopped)

        self.assertFalse(tracker.register(1.08))
        self.assertTrue(tracker.stopped)
        self.assertIsNotNone(tracker.stop_reason)

    def test_summarize_action_usage_computes_percentages(self) -> None:
        usage = summarize_action_usage(
            action_counts=Counter({0: 3, 1: 1}),
            action_labels=("ATTACK", "MOVE_LEFT+ATTACK"),
        )
        self.assertEqual(usage[0]["label"], "ATTACK")
        self.assertEqual(usage[0]["count"], 3)
        self.assertAlmostEqual(usage[0]["percentage"], 75.0)

    def test_periodic_evaluation_reseeds_eval_env_before_scoring(self) -> None:
        profile = get_training_profile("default")
        eval_env = FakeVecEnv()
        callback = PeriodicTrainingCallback(
            run_id="run-1",
            profile_name="default",
            profile=profile,
            auto_checkpoint_dir=Path("artifacts/checkpoints/auto"),
            compatibility_auto_checkpoint_dir=Path("artifacts/checkpoints/auto-compat"),
            evaluation_settings=EvaluationSettings(
                frequency=25000,
                episodes=20,
                save_best=False,
                best_checkpoint_stem=Path("artifacts/checkpoints/doom_foundation_agent_best"),
                compatibility_best_checkpoint_stem=Path(
                    "artifacts/checkpoints/doom_foundation_agent_best_compat"
                ),
                seed=profile.seed + 1,
            ),
            eval_env=cast(VecEnv, eval_env),
            resume_state=ResumeState(mode="from_scratch", checkpoint=None),
            verbose=0,
        )
        callback.model = cast(BaseAlgorithm, FakeModel())

        with patch(
            "doom_agent.services.training_support.evaluate_policy",
            return_value=([1.0, 3.0], [10, 20]),
        ):
            callback._run_periodic_evaluation()

        self.assertEqual(eval_env.seed_calls, [profile.seed + 1])

    def test_periodic_evaluation_records_presentation_metrics(self) -> None:
        profile = get_training_profile("default")
        eval_env = FakeVecEnv()
        callback = PeriodicTrainingCallback(
            run_id="run-1",
            profile_name="default",
            profile=profile,
            auto_checkpoint_dir=Path("artifacts/checkpoints/auto"),
            compatibility_auto_checkpoint_dir=Path("artifacts/checkpoints/auto-compat"),
            evaluation_settings=EvaluationSettings(
                frequency=25000,
                episodes=20,
                save_best=False,
                best_checkpoint_stem=Path("artifacts/checkpoints/doom_foundation_agent_best"),
                compatibility_best_checkpoint_stem=Path(
                    "artifacts/checkpoints/doom_foundation_agent_best_compat"
                ),
                seed=profile.seed + 1,
            ),
            eval_env=cast(VecEnv, eval_env),
            resume_state=ResumeState(mode="from_scratch", checkpoint=None),
            verbose=0,
        )
        fake_model = FakeModel()
        callback.model = cast(BaseAlgorithm, fake_model)
        callback.action_labels = ("ATTACK", "MOVE_LEFT+ATTACK")
        callback.action_counts = Counter({0: 6, 1: 4})

        with patch(
            "doom_agent.services.training_support.evaluate_policy",
            return_value=([1.0, 3.0], [10, 20]),
        ):
            callback._run_periodic_evaluation()

        recorded = dict(fake_model.logger.records)
        self.assertEqual(recorded["eval/episodes"], 20)
        self.assertEqual(recorded["eval/evaluation_index"], 1)
        self.assertIn("eval/best_mean_reward_so_far", recorded)
        self.assertIn("eval/reward_gap_vs_best", recorded)
        self.assertEqual(recorded["eval/is_new_best"], 1.0)
        self.assertEqual(recorded["eval/actions/unique_top_actions"], 2)
        self.assertEqual(recorded["eval/actions/dominant_action_percentage"], 60.0)
        self.assertEqual(recorded["eval/actions/attack_percentage"], 60.0)
        self.assertEqual(recorded["eval/actions/move_left_attack_percentage"], 40.0)

    def test_load_best_mean_reward_uses_resume_checkpoint_when_run_best_missing(self) -> None:
        from doom_agent.services.training_support import load_best_mean_reward
        from doom_agent.utils.checkpoints import ResolvedCheckpoint

        checkpoint = ResolvedCheckpoint(
            checkpoint_stem=Path("artifacts/checkpoints/resume_model"),
            metadata={
                "profile_name": "default",
                "run_id": "run-1",
                "saved_timesteps": 2048,
                "saved_at_utc": "2026-01-01T00:00:00+00:00",
                "profile": get_training_profile("default").to_dict(),
                "resume_source": None,
                "resume_saved_timesteps": None,
                "training_status": "completed",
                "checkpoint_role": "best",
                "evaluation_source": "training_internal",
                "canonical_checkpoint_path": "artifacts/checkpoints/resume_model.zip",
                "evaluation_metrics": {
                    "mean_reward": -10.0,
                    "std_reward": 1.0,
                    "mean_episode_length": 20.0,
                    "episodes": 20,
                },
                "is_best_checkpoint": True,
            },
            saved_timesteps=2048,
        )

        best_mean_reward = load_best_mean_reward(
            Path("artifacts/checkpoints/missing_best"),
            resume_checkpoint=checkpoint,
        )

        self.assertEqual(best_mean_reward, -10.0)
