from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

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
from doom_agent.persistence.config import (
    DATABASE_URL_ENV_VAR,
    get_database_url,
    load_env_file,
)
from doom_agent.storage.config import (
    DEFAULT_STORAGE_BACKEND,
    S3_ACCESS_KEY_ID_ENV_VAR,
    S3_BUCKET_ENV_VAR,
    S3_REGION_ENV_VAR,
    S3_SECRET_ACCESS_KEY_ENV_VAR,
    get_s3_settings,
    get_storage_backend,
    has_explicit_s3_config,
)


class TrainingProfileTests(unittest.TestCase):
    def test_training_catalog_is_loaded_from_split_toml(self) -> None:
        catalog = load_training_catalog()
        self.assertIn("default", catalog.profiles)
        self.assertEqual(tuple(catalog.profiles), ("default",))
        self.assertEqual(
            tuple(catalog.scenarios),
            (
                "basic",
                "basic_audio",
                "basic_notifications",
                "defend_the_center",
                "defend_the_line",
                "health_gathering",
                "my_way_home",
                "take_cover",
            ),
        )

    def test_project_paths_include_local_runs_directory(self) -> None:
        project_paths = build_project_paths()
        self.assertEqual(project_paths.runs_dir, project_paths.artifacts_dir / "runs")

    def test_default_is_only_public_profile(self) -> None:
        self.assertEqual(PUBLIC_PROFILE_NAMES, ("default",))
        self.assertEqual(set(PUBLIC_PROFILE_NAMES) | set(ADVANCED_PROFILE_NAMES), set(PROFILE_NAMES))
        self.assertEqual(ADVANCED_PROFILE_NAMES, ())

    def test_requested_timesteps_are_rounded_explicitly(self) -> None:
        profile = get_training_profile("default", requested_timesteps=8)
        self.assertEqual(profile.requested_timesteps, 8)
        self.assertEqual(profile.effective_timesteps, 2048)
        self.assertTrue(profile.uses_rounded_timesteps)

    def test_normal_training_defaults_to_headless_mode(self) -> None:
        profile = get_training_profile("default")
        self.assertFalse(profile.render)
        self.assertTrue(profile.record_video)

    def test_basic_scenario_uses_combat_action_preset(self) -> None:
        profile = get_training_profile("default")
        self.assertEqual(profile.action_combo_preset, "basic_combat")
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

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

    def test_basic_scenario_defines_optimized_training_parameters(self) -> None:
        profile = get_training_profile("default")
        self.assertEqual(profile.requested_timesteps, 1500000)
        self.assertEqual(profile.learning_rate, 0.0001)
        self.assertEqual(profile.n_steps, 2048)
        self.assertEqual(profile.batch_size, 128)
        self.assertEqual(profile.n_epochs, 4)
        self.assertEqual(profile.ent_coef, 0.01)
        self.assertEqual(profile.checkpoint_frequency, 50000)
        self.assertEqual(profile.eval_frequency, 25000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.video_record_frequency, 200000)
        self.assertEqual(profile.video_length, 1000)

    def test_defend_the_center_scenario_uses_turn_combat_profile(self) -> None:
        profile = get_training_profile("default", scenario_name="defend_the_center")
        self.assertEqual(profile.scenario_name, "defend_the_center.cfg")
        self.assertEqual(profile.action_combo_preset, "turn_combat")
        self.assertEqual(profile.requested_timesteps, 300000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_basic_audio_scenario_uses_basic_combat_profile(self) -> None:
        profile = get_training_profile("default", scenario_name="basic_audio")
        self.assertEqual(profile.scenario_name, "basic_audio.cfg")
        self.assertEqual(profile.action_combo_preset, "basic_combat")
        self.assertEqual(profile.observation_mode, "vision_audio")
        self.assertEqual(profile.requested_timesteps, 300000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_basic_notifications_scenario_uses_basic_combat_profile(self) -> None:
        profile = get_training_profile("default", scenario_name="basic_notifications")
        self.assertEqual(profile.scenario_name, "basic_notifications.cfg")
        self.assertEqual(profile.action_combo_preset, "basic_combat")
        self.assertEqual(profile.observation_mode, "vision_notifications")
        self.assertEqual(profile.requested_timesteps, 300000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_health_gathering_scenario_uses_navigation_profile(self) -> None:
        profile = get_training_profile("default", scenario_name="health_gathering")
        self.assertEqual(profile.scenario_name, "health_gathering.cfg")
        self.assertEqual(profile.action_combo_preset, "health_navigation")
        self.assertEqual(profile.requested_timesteps, 300000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_take_cover_scenario_uses_dodge_profile(self) -> None:
        profile = get_training_profile("default", scenario_name="take_cover")
        self.assertEqual(profile.scenario_name, "take_cover.cfg")
        self.assertEqual(profile.action_combo_preset, "take_cover_dodge")
        self.assertEqual(profile.requested_timesteps, 300000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_my_way_home_scenario_uses_navigation_profile(self) -> None:
        profile = get_training_profile("default", scenario_name="my_way_home")
        self.assertEqual(profile.scenario_name, "my_way_home.cfg")
        self.assertEqual(profile.action_combo_preset, "my_way_home_navigation")
        self.assertEqual(profile.requested_timesteps, 300000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_defend_the_line_scenario_uses_turn_combat_profile(self) -> None:
        profile = get_training_profile("default", scenario_name="defend_the_line")
        self.assertEqual(profile.scenario_name, "defend_the_line.cfg")
        self.assertEqual(profile.action_combo_preset, "turn_combat")
        self.assertEqual(profile.requested_timesteps, 300000)
        self.assertEqual(profile.eval_episodes, 20)
        self.assertEqual(profile.reward_shaping.clip_min, -1.0)
        self.assertEqual(profile.reward_shaping.clip_max, 1.0)

    def test_profile_roundtrip_preserves_evaluation_defaults(self) -> None:
        profile = get_training_profile("default")
        roundtripped = type(profile).from_dict(profile.to_dict())
        self.assertEqual(roundtripped.eval_frequency, profile.eval_frequency)
        self.assertEqual(roundtripped.eval_episodes, profile.eval_episodes)

    def test_profiles_are_valid_against_existing_scenarios(self) -> None:
        project_paths = build_project_paths()
        for profile_name in PROFILE_NAMES:
            with self.subTest(profile=profile_name):
                get_training_profile(profile_name).validate(project_paths)

        for scenario_name in SCENARIO_NAMES:
            with self.subTest(scenario=scenario_name):
                get_training_profile("default", scenario_name=scenario_name).validate(project_paths)

    def test_database_url_can_be_loaded_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                'AGENTE_DOOM_DATABASE_URL="postgresql+psycopg://user:pass@host/db?sslmode=require"\n',
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                load_env_file(env_path)
                self.assertEqual(
                    get_database_url(),
                    "postgresql+psycopg://user:pass@host/db?sslmode=require",
                )

    def test_database_url_prefers_real_environment_over_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                'AGENTE_DOOM_DATABASE_URL="postgresql+psycopg://file:user@host/db?sslmode=require"\n',
                encoding="utf-8",
            )

            with patch.dict(
                "os.environ",
                {DATABASE_URL_ENV_VAR: "postgresql+psycopg://env:user@host/db?sslmode=require"},
                clear=True,
            ):
                load_env_file(env_path)
                self.assertEqual(
                    get_database_url(),
                    "postgresql+psycopg://env:user@host/db?sslmode=require",
                )

    def test_storage_backend_defaults_to_s3(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("doom_agent.storage.config.load_env_file", return_value=None),
        ):
            self.assertEqual(get_storage_backend(), DEFAULT_STORAGE_BACKEND)

    def test_storage_backend_rejects_non_s3_values(self) -> None:
        with (
            patch.dict("os.environ", {"AGENTE_DOOM_STORAGE_BACKEND": "minio"}, clear=True),
            patch("doom_agent.storage.config.load_env_file", return_value=None),
        ):
            with self.assertRaises(RuntimeError):
                get_storage_backend()

    def test_s3_settings_can_be_loaded_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        'AGENTE_DOOM_STORAGE_BACKEND="s3"',
                        'AGENTE_DOOM_S3_BUCKET="agente-doom-artifacts-prod"',
                        'AGENTE_DOOM_S3_REGION="us-east-1"',
                        'AGENTE_DOOM_S3_ACCESS_KEY_ID="AKIAEXAMPLE"',
                        'AGENTE_DOOM_S3_SECRET_ACCESS_KEY="secret-example"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                load_env_file(env_path)
                self.assertEqual(get_storage_backend(), "s3")
                self.assertTrue(has_explicit_s3_config())
                settings = get_s3_settings()
                self.assertEqual(settings.bucket_name, "agente-doom-artifacts-prod")
                self.assertEqual(settings.region, "us-east-1")
                self.assertEqual(settings.object_prefix, "runs")

    def test_s3_settings_prefer_real_environment_over_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        'AGENTE_DOOM_STORAGE_BACKEND="s3"',
                        'AGENTE_DOOM_S3_BUCKET="file-bucket"',
                        'AGENTE_DOOM_S3_REGION="us-east-1"',
                        'AGENTE_DOOM_S3_ACCESS_KEY_ID="file-access-key"',
                        'AGENTE_DOOM_S3_SECRET_ACCESS_KEY="file-secret"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.dict(
                "os.environ",
                {
                    S3_BUCKET_ENV_VAR: "env-bucket",
                    S3_REGION_ENV_VAR: "us-east-1",
                    S3_ACCESS_KEY_ID_ENV_VAR: "env-access-key",
                    S3_SECRET_ACCESS_KEY_ENV_VAR: "env-secret",
                },
                clear=True,
            ):
                load_env_file(env_path)
                settings = get_s3_settings()
                self.assertEqual(settings.bucket_name, "env-bucket")
                self.assertEqual(settings.access_key_id, "env-access-key")
