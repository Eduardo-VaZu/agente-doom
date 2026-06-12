from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doom_agent.config import (
    ADVANCED_PROFILE_NAMES,
    PROFILE_NAMES,
    PUBLIC_PROFILE_NAMES,
    SCENARIO_NAMES,
    build_project_paths,
    get_training_profile,
    load_training_catalog,
)
from doom_agent.config.schema import RewardShapingConfig


class TrainingProfileTests(unittest.TestCase):
    def test_training_catalog_is_loaded_from_toml(self) -> None:
        catalog = load_training_catalog()
        self.assertIn("default", catalog.profiles)
        self.assertIn("deadly_corridor", catalog.scenarios)

    def test_default_is_only_public_profile(self) -> None:
        self.assertEqual(PUBLIC_PROFILE_NAMES, ("default",))
        self.assertEqual(set(PUBLIC_PROFILE_NAMES) | set(ADVANCED_PROFILE_NAMES), set(PROFILE_NAMES))
        self.assertEqual(ADVANCED_PROFILE_NAMES, ())

    def test_requested_timesteps_are_rounded_explicitly(self) -> None:
        profile = get_training_profile("default", requested_timesteps=8)
        self.assertEqual(profile.requested_timesteps, 8)
        self.assertEqual(profile.effective_timesteps, 2048)
        self.assertTrue(profile.uses_rounded_timesteps)

    def test_profile_can_be_materialized_for_another_scenario(self) -> None:
        profile = get_training_profile("default", scenario_name="deadly_corridor")
        self.assertEqual(profile.scenario_key, "deadly_corridor")
        self.assertEqual(profile.scenario_name, "deadly_corridor.cfg")
        self.assertEqual(profile.action_combo_preset, "basic_combat")
        self.assertIn("__deadly_corridor", profile.checkpoint_name)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_normal_training_defaults_to_visible_mode(self) -> None:
        profile = get_training_profile("default")
        self.assertTrue(profile.render)
        self.assertTrue(profile.record_video)

    def test_basic_scenario_uses_combat_action_preset(self) -> None:
        profile = get_training_profile("default")
        self.assertEqual(profile.action_combo_preset, "basic_combat")

    def test_scenarios_use_focused_action_presets(self) -> None:
        self.assertEqual(
            get_training_profile("default", scenario_name="deadly_corridor").action_combo_preset,
            "basic_combat",
        )
        self.assertEqual(
            get_training_profile("default", scenario_name="defend_the_center").action_combo_preset,
            "turn_combat",
        )
        self.assertEqual(
            get_training_profile("default", scenario_name="health_gathering").action_combo_preset,
            "health_navigation",
        )

    def test_reward_shaping_applies_scale_offset_and_clip(self) -> None:
        shaping = RewardShapingConfig(scale=0.5, offset=1.0, clip_min=-2.0, clip_max=3.0)
        self.assertEqual(shaping.apply(2.0), 1.5)
        self.assertEqual(shaping.apply(10.0), 3.0)
        self.assertEqual(shaping.apply(-10.0), -2.0)

    def test_profile_supports_seed_default_and_override(self) -> None:
        default_profile = get_training_profile("default")
        custom_profile = get_training_profile("default", seed=123)
        self.assertEqual(default_profile.seed, 42)
        self.assertEqual(custom_profile.seed, 123)

    def test_scenarios_define_optimized_training_parameters(self) -> None:
        expected_timesteps = {
            "basic": 500000,
            "defend_the_center": 250000,
            "deadly_corridor": 300000,
            "health_gathering": 150000,
        }
        for scenario_name, timesteps in expected_timesteps.items():
            with self.subTest(scenario=scenario_name):
                profile = get_training_profile("default", scenario_name=scenario_name)
                self.assertEqual(profile.requested_timesteps, timesteps)
                self.assertEqual(profile.learning_rate, 0.0001)
                self.assertEqual(profile.n_steps, 2048)
                self.assertEqual(profile.batch_size, 64)
                self.assertEqual(profile.n_epochs, 10)

    def test_profiles_are_valid_against_existing_scenarios(self) -> None:
        project_paths = build_project_paths()
        for profile_name in PROFILE_NAMES:
            with self.subTest(profile=profile_name):
                get_training_profile(profile_name).validate(project_paths)

        for scenario_name in SCENARIO_NAMES:
            with self.subTest(scenario=scenario_name):
                get_training_profile("default", scenario_name=scenario_name).validate(project_paths)
