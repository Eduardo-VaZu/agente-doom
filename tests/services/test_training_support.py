from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

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
    def record(self, _key: str, _value: float) -> None:
        return None


class FakeModel:
    def __init__(self) -> None:
        self.logger = FakeLogger()


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
            profile_name="default",
            profile=profile,
            auto_checkpoint_dir=Path("artifacts/checkpoints/auto"),
            evaluation_settings=EvaluationSettings(
                frequency=25000,
                episodes=20,
                save_best=False,
                best_checkpoint_stem=Path("artifacts/checkpoints/doom_foundation_agent_best"),
                seed=profile.seed + 1,
            ),
            eval_env=eval_env,
            resume_state=ResumeState(mode="from_scratch", checkpoint=None),
            verbose=0,
        )
        callback.model = FakeModel()

        with patch(
            "doom_agent.services.training_support.evaluate_policy",
            return_value=([1.0, 3.0], [10, 20]),
        ):
            callback._run_periodic_evaluation()

        self.assertEqual(eval_env.seed_calls, [profile.seed + 1])
