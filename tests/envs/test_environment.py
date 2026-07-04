from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import gymnasium as gym
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.envs import make_vectorized_env
from doom_agent.envs.doom_env import build_button_combination_actions, has_opposing_buttons


class EnvironmentSmokeTests(unittest.TestCase):
    def test_environment_reset_and_step_supports_button_combinations(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default")
        env = make_vectorized_env(profile, project_paths)

        try:
            observation = cast(np.ndarray, env.reset())
            self.assertEqual(
                observation.shape,
                (1, profile.frame_stack, profile.screen_height, profile.screen_width),
            )
            self.assertIsInstance(env.action_space, gym.spaces.Discrete)
            discrete_action_space = cast(gym.spaces.Discrete[Any], env.action_space)
            self.assertEqual(discrete_action_space.n, 3)
            self.assertNotIn("NOOP", env.get_attr("action_labels")[0])
            self.assertNotIn("MOVE_LEFT", env.get_attr("action_labels")[0])
            self.assertNotIn("MOVE_RIGHT", env.get_attr("action_labels")[0])
            self.assertIn("ATTACK", env.get_attr("action_labels")[0])
            self.assertIn("MOVE_LEFT+ATTACK", env.get_attr("action_labels")[0])
            self.assertIn("MOVE_RIGHT+ATTACK", env.get_attr("action_labels")[0])

            step_result = env.step(np.array([1], dtype=np.int64))
            observation = cast(np.ndarray, step_result[0])
            rewards, dones = step_result[1], step_result[2]
            self.assertEqual(
                observation.shape,
                (1, profile.frame_stack, profile.screen_height, profile.screen_width),
            )
            self.assertEqual(rewards.shape, (1,))
            self.assertEqual(dones.shape, (1,))
        finally:
            env.close()

    def test_environment_still_supports_legacy_multidiscrete_actions(self) -> None:
        project_paths = build_project_paths()
        profile = replace(get_training_profile("default"), action_space_kind="multidiscrete")
        env = make_vectorized_env(profile, project_paths)

        try:
            env.reset()
            step_result = env.step(np.array([[1, 0, 1]], dtype=np.int64))
            observation = cast(np.ndarray, step_result[0])
            self.assertEqual(
                observation.shape,
                (1, profile.frame_stack, profile.screen_height, profile.screen_width),
            )
        finally:
            env.close()

    def test_button_combination_actions_exclude_opposites(self) -> None:
        labels, actions = build_button_combination_actions(
            ("MOVE_LEFT", "MOVE_RIGHT", "ATTACK")
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 6)
        self.assertIn("NOOP", readable_labels)
        self.assertIn("MOVE_LEFT", readable_labels)
        self.assertIn("MOVE_RIGHT", readable_labels)
        self.assertIn("ATTACK", readable_labels)
        self.assertIn("MOVE_LEFT+ATTACK", readable_labels)
        self.assertIn("MOVE_RIGHT+ATTACK", readable_labels)
        self.assertFalse(any(has_opposing_buttons(set(label)) for label in labels))

    def test_basic_combat_actions_only_include_attack_actions(self) -> None:
        labels, actions = build_button_combination_actions(
            ("MOVE_LEFT", "MOVE_RIGHT", "ATTACK"),
            preset="basic_combat",
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 3)
        self.assertEqual(
            readable_labels,
            ("ATTACK", "MOVE_LEFT+ATTACK", "MOVE_RIGHT+ATTACK"),
        )
        self.assertTrue(all("ATTACK" in label for label in labels))

    def test_turn_combat_actions_only_include_attack_actions(self) -> None:
        labels, actions = build_button_combination_actions(
            ("TURN_LEFT", "TURN_RIGHT", "ATTACK"),
            preset="turn_combat",
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 3)
        self.assertEqual(
            readable_labels,
            ("ATTACK", "TURN_LEFT+ATTACK", "TURN_RIGHT+ATTACK"),
        )
        self.assertTrue(all("ATTACK" in label for label in labels))

    def test_health_navigation_actions_keep_moving_forward(self) -> None:
        labels, actions = build_button_combination_actions(
            ("TURN_LEFT", "TURN_RIGHT", "MOVE_FORWARD"),
            preset="health_navigation",
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 3)
        self.assertEqual(
            readable_labels,
            ("MOVE_FORWARD", "TURN_LEFT+MOVE_FORWARD", "TURN_RIGHT+MOVE_FORWARD"),
        )
        self.assertTrue(all("MOVE_FORWARD" in label for label in labels))

    def test_take_cover_dodge_actions_only_include_lateral_movement(self) -> None:
        labels, actions = build_button_combination_actions(
            ("MOVE_LEFT", "MOVE_RIGHT"),
            preset="take_cover_dodge",
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 2)
        self.assertEqual(readable_labels, ("MOVE_LEFT", "MOVE_RIGHT"))

    def test_basic_action_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("ATTACK", "MOVE_LEFT+ATTACK", "MOVE_RIGHT+ATTACK"),
            )
        finally:
            env.close()

    def test_defend_the_center_turn_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="defend_the_center")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("ATTACK", "TURN_LEFT+ATTACK", "TURN_RIGHT+ATTACK"),
            )
        finally:
            env.close()

    def test_basic_audio_action_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="basic_audio")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("ATTACK", "MOVE_LEFT+ATTACK", "MOVE_RIGHT+ATTACK"),
            )
        finally:
            env.close()

    def test_basic_notifications_action_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="basic_notifications")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("ATTACK", "MOVE_LEFT+ATTACK", "MOVE_RIGHT+ATTACK"),
            )
        finally:
            env.close()

    def test_health_gathering_navigation_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="health_gathering")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("MOVE_FORWARD", "TURN_LEFT+MOVE_FORWARD", "TURN_RIGHT+MOVE_FORWARD"),
            )
        finally:
            env.close()

    def test_take_cover_dodge_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="take_cover")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(env.get_attr("action_labels")[0], ("MOVE_LEFT", "MOVE_RIGHT"))
        finally:
            env.close()

    def test_defend_the_line_turn_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="defend_the_line")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("ATTACK", "TURN_LEFT+ATTACK", "TURN_RIGHT+ATTACK"),
            )
        finally:
            env.close()
