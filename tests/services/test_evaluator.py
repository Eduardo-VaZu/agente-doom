from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import get_training_profile
from doom_agent.services.evaluator import evaluate


class FakeVecEnv:
    def __init__(self) -> None:
        self.seed_value: int | None = None
        self.closed = False

    def seed(self, seed: int) -> None:
        self.seed_value = seed

    def close(self) -> None:
        self.closed = True


class EvaluatorTests(unittest.TestCase):
    def test_offline_evaluate_returns_json_summary(self) -> None:
        profile = get_training_profile("default").for_evaluation(render=False)
        env = FakeVecEnv()

        with (
            patch(
                "doom_agent.services.evaluator.resolve_profile_for_evaluation",
                return_value=(profile, Path("artifacts/checkpoints/doom_foundation_agent_best")),
            ),
            patch("doom_agent.services.evaluator.make_vectorized_env", return_value=env),
            patch("doom_agent.services.evaluator.RecurrentPPO.load", return_value=object()),
            patch(
                "doom_agent.services.evaluator.evaluate_policy",
                return_value=([1.0, 3.0], [10, 20]),
            ),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                summary = evaluate(
                    checkpoint_name="doom_foundation_agent",
                    episodes=2,
                    render=False,
                    json_output=True,
                )

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["metrics"]["mean_reward"], 2.0)
        self.assertEqual(summary["metrics"]["std_reward"], 1.0)
        self.assertEqual(summary["metrics"]["mean_episode_length"], 15.0)
        self.assertEqual(summary["metrics"]["episodes"], 2)
        self.assertFalse(summary["render"])
        self.assertEqual(env.seed_value, profile.seed + 1)
        self.assertTrue(env.closed)

        rendered_output = json.loads(stdout.getvalue())
        self.assertEqual(rendered_output["metrics"]["mean_reward"], 2.0)

    def test_evaluate_rejects_steps_and_episodes_together(self) -> None:
        with self.assertRaises(ValueError):
            evaluate(steps=10, episodes=2)
