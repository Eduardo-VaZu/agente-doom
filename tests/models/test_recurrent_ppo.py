from __future__ import annotations

import sys
import unittest
from pathlib import Path

import gymnasium as gym
import numpy as np
import torch as th

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.envs import make_vectorized_env
from doom_agent.models.recurrent_ppo import (
    DoomFeatureExtractor,
    DoomMultiModalFeatureExtractor,
    build_recurrent_ppo_model,
)


class DoomMultiModalFeatureExtractorTests(unittest.TestCase):
    def test_forward_pass_produces_expected_feature_dim(self) -> None:
        observation_space = gym.spaces.Dict(
            {
                "image": gym.spaces.Box(low=0, high=255, shape=(4, 84, 84), dtype=np.uint8),
                "features": gym.spaces.Box(low=-1.0, high=1.0, shape=(16,), dtype=np.float32),
            }
        )
        extractor = DoomMultiModalFeatureExtractor(observation_space, features_dim=512)

        batch = {
            "image": th.zeros((2, 4, 84, 84)),
            "features": th.zeros((2, 16)),
        }
        output = extractor(batch)

        self.assertEqual(tuple(output.shape), (2, 512))


class BuildRecurrentPpoModelPolicySelectionTests(unittest.TestCase):
    def test_selects_multi_input_policy_for_dict_observation_scenario(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="basic_audio")
        env = make_vectorized_env(profile, project_paths)
        try:
            model = build_recurrent_ppo_model(env, profile, tensorboard_log_dir="")
            self.assertEqual(type(model.policy).__name__, "RecurrentMultiInputActorCriticPolicy")
            self.assertIsInstance(model.policy.features_extractor, DoomMultiModalFeatureExtractor)
        finally:
            env.close()

    def test_selects_cnn_policy_for_box_observation_scenario(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default")
        env = make_vectorized_env(profile, project_paths)
        try:
            model = build_recurrent_ppo_model(env, profile, tensorboard_log_dir="")
            self.assertEqual(type(model.policy).__name__, "RecurrentActorCriticCnnPolicy")
            self.assertIsInstance(model.policy.features_extractor, DoomFeatureExtractor)
        finally:
            env.close()
