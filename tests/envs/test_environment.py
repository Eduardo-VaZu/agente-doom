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
from doom_agent.envs.doom_env import (
    NOTIFICATION_VOCABULARY,
    bucket_position,
    build_button_combination_actions,
    compute_exploration_bonus,
    decayed_exploration_bonus,
    extract_audio_features,
    extract_notification_features,
    has_opposing_buttons,
    parse_notification_label,
)


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

    def test_corridor_combat_actions_cover_navigation_and_attack(self) -> None:
        labels, actions = build_button_combination_actions(
            ("MOVE_LEFT", "MOVE_RIGHT", "ATTACK", "MOVE_FORWARD", "MOVE_BACKWARD", "TURN_LEFT", "TURN_RIGHT"),
            preset="corridor_combat",
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 8)
        self.assertEqual(
            readable_labels,
            (
                "ATTACK",
                "MOVE_FORWARD",
                "MOVE_FORWARD+ATTACK",
                "MOVE_BACKWARD",
                "TURN_LEFT",
                "TURN_RIGHT",
                "MOVE_LEFT",
                "MOVE_RIGHT",
            ),
        )

    def test_full_doom_basic_actions_cover_navigation_use_and_weapon_cycle(self) -> None:
        labels, actions = build_button_combination_actions(
            (
                "ATTACK",
                "USE",
                "MOVE_RIGHT",
                "MOVE_LEFT",
                "MOVE_BACKWARD",
                "MOVE_FORWARD",
                "TURN_RIGHT",
                "TURN_LEFT",
                "SELECT_NEXT_WEAPON",
            ),
            preset="full_doom_basic",
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 10)
        self.assertEqual(
            readable_labels,
            (
                "ATTACK",
                "MOVE_FORWARD",
                "MOVE_FORWARD+ATTACK",
                "MOVE_BACKWARD",
                "TURN_LEFT",
                "TURN_RIGHT",
                "MOVE_LEFT",
                "MOVE_RIGHT",
                "USE",
                "SELECT_NEXT_WEAPON",
            ),
        )

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

    def test_my_way_home_navigation_actions_cover_turns_and_strafes(self) -> None:
        labels, actions = build_button_combination_actions(
            ("TURN_LEFT", "TURN_RIGHT", "MOVE_FORWARD", "MOVE_LEFT", "MOVE_RIGHT"),
            preset="my_way_home_navigation",
        )
        readable_labels = tuple("+".join(label) for label in labels)

        self.assertEqual(len(actions), 5)
        self.assertEqual(
            readable_labels,
            ("MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "MOVE_LEFT", "MOVE_RIGHT"),
        )

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
            observation = cast(dict[str, np.ndarray], env.reset())
            self.assertEqual(
                observation["image"].shape,
                (1, profile.frame_stack, profile.screen_height, profile.screen_width),
            )
            self.assertEqual(observation["features"].shape, (1, profile.frame_stack * 4))
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
            observation = cast(dict[str, np.ndarray], env.reset())
            self.assertEqual(
                observation["image"].shape,
                (1, profile.frame_stack, profile.screen_height, profile.screen_width),
            )
            self.assertEqual(
                observation["features"].shape,
                (1, profile.frame_stack * len(NOTIFICATION_VOCABULARY)),
            )
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

    def test_health_gathering_supreme_navigation_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="health_gathering_supreme")
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

    def test_my_way_home_navigation_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="my_way_home")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "MOVE_LEFT", "MOVE_RIGHT"),
            )
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

    def test_bucket_position_groups_nearby_coordinates_into_same_cell(self) -> None:
        self.assertEqual(bucket_position(10.0, 20.0, grid_size=48.0), (0, 0))
        self.assertEqual(bucket_position(47.9, 47.9, grid_size=48.0), (0, 0))
        self.assertEqual(bucket_position(48.0, 0.0, grid_size=48.0), (1, 0))
        self.assertEqual(bucket_position(-1.0, -1.0, grid_size=48.0), (-1, -1))

    def test_compute_exploration_bonus_rewards_new_cells_only_once(self) -> None:
        visited: set[tuple[int, int]] = set()

        first_visit = compute_exploration_bonus((0, 0), visited, bonus=0.02)
        second_visit = compute_exploration_bonus((0, 0), visited, bonus=0.02)
        new_cell_visit = compute_exploration_bonus((1, 0), visited, bonus=0.02)

        self.assertEqual(first_visit, 0.02)
        self.assertEqual(second_visit, 0.0)
        self.assertEqual(new_cell_visit, 0.02)
        self.assertEqual(visited, {(0, 0), (1, 0)})

    def test_decayed_exploration_bonus_linearly_reduces_to_zero(self) -> None:
        self.assertEqual(decayed_exploration_bonus(0.02, 0, 100), 0.02)
        self.assertAlmostEqual(decayed_exploration_bonus(0.02, 50, 100), 0.01)
        self.assertEqual(decayed_exploration_bonus(0.02, 100, 100), 0.0)
        self.assertEqual(decayed_exploration_bonus(0.02, 200, 100), 0.0)

    def test_decayed_exploration_bonus_disabled_stays_constant(self) -> None:
        self.assertEqual(decayed_exploration_bonus(0.02, 500, 0), 0.02)

    def test_extract_audio_features_returns_zeros_for_missing_buffer(self) -> None:
        features = extract_audio_features(None)
        self.assertEqual(features.shape, (4,))
        self.assertTrue(np.array_equal(features, np.zeros(4, dtype=np.float32)))

    def test_extract_audio_features_detects_left_louder_than_right(self) -> None:
        loud_left = np.zeros((100, 2), dtype=np.int16)
        loud_left[:, 0] = 20000
        loud_left[:, 1] = 2000

        features = extract_audio_features(loud_left)

        rms_left, rms_right, pan, loudness = features
        self.assertGreater(rms_left, rms_right)
        self.assertGreater(pan, 0.0)
        self.assertGreater(loudness, 0.0)
        self.assertTrue(np.all(np.abs(features) <= 1.0))

    def test_extract_audio_features_silence_has_zero_pan_and_loudness(self) -> None:
        silence = np.zeros((100, 2), dtype=np.int16)
        features = extract_audio_features(silence)
        self.assertTrue(np.array_equal(features, np.zeros(4, dtype=np.float32)))

    def test_parse_notification_label_strips_prefix_and_suffix(self) -> None:
        self.assertEqual(parse_notification_label("Shoot: Cacodemon\n"), "Cacodemon")
        self.assertEqual(parse_notification_label(""), "")
        self.assertEqual(parse_notification_label(None), "")

    def test_extract_notification_features_one_hot_encodes_known_label(self) -> None:
        features = extract_notification_features("Shoot: Demon\n")
        expected = np.zeros(len(NOTIFICATION_VOCABULARY), dtype=np.float32)
        expected[NOTIFICATION_VOCABULARY.index("Demon")] = 1.0
        self.assertTrue(np.array_equal(features, expected))

    def test_extract_notification_features_empty_text_selects_empty_slot(self) -> None:
        features = extract_notification_features("")
        expected = np.zeros(len(NOTIFICATION_VOCABULARY), dtype=np.float32)
        expected[NOTIFICATION_VOCABULARY.index("")] = 1.0
        self.assertTrue(np.array_equal(features, expected))

    def test_extract_notification_features_unknown_label_returns_zeros(self) -> None:
        features = extract_notification_features("Shoot: Cyberdemon\n")
        self.assertTrue(np.array_equal(features, np.zeros(len(NOTIFICATION_VOCABULARY), dtype=np.float32)))

    def test_environment_tracks_visited_cells_after_reset_when_exploration_bonus_enabled(
        self,
    ) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="my_way_home")
        profile = replace(profile, exploration_bonus=0.02)
        env = make_vectorized_env(profile, project_paths)
        try:
            env.reset()
            self.assertEqual(len(env.get_attr("_visited_cells")[0]), 1)
        finally:
            env.close()

    def test_environment_does_not_track_visited_cells_when_exploration_bonus_disabled(
        self,
    ) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="my_way_home")
        env = make_vectorized_env(profile, project_paths)
        try:
            env.reset()
            self.assertEqual(len(env.get_attr("_visited_cells")[0]), 0)
        finally:
            env.close()

    def test_predict_position_turn_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="predict_position")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                ("ATTACK", "TURN_LEFT+ATTACK", "TURN_RIGHT+ATTACK"),
            )
        finally:
            env.close()

    def test_deadly_corridor_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="deadly_corridor")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("action_labels")[0],
                (
                    "ATTACK",
                    "MOVE_FORWARD",
                    "MOVE_FORWARD+ATTACK",
                    "MOVE_BACKWARD",
                    "TURN_LEFT",
                    "TURN_RIGHT",
                    "MOVE_LEFT",
                    "MOVE_RIGHT",
                ),
            )
        finally:
            env.close()

    def test_full_level_map01_preset_matches_available_buttons(self) -> None:
        project_paths = build_project_paths()
        profile = get_training_profile("default", scenario_name="full_level_map01")
        env = make_vectorized_env(profile, project_paths)
        try:
            self.assertEqual(
                env.get_attr("available_button_names")[0],
                (
                    "ATTACK",
                    "USE",
                    "MOVE_RIGHT",
                    "MOVE_LEFT",
                    "MOVE_BACKWARD",
                    "MOVE_FORWARD",
                    "TURN_RIGHT",
                    "TURN_LEFT",
                    "SELECT_NEXT_WEAPON",
                ),
            )
            self.assertEqual(
                env.get_attr("action_labels")[0],
                (
                    "ATTACK",
                    "MOVE_FORWARD",
                    "MOVE_FORWARD+ATTACK",
                    "MOVE_BACKWARD",
                    "TURN_LEFT",
                    "TURN_RIGHT",
                    "MOVE_LEFT",
                    "MOVE_RIGHT",
                    "USE",
                    "SELECT_NEXT_WEAPON",
                ),
            )
        finally:
            env.close()
