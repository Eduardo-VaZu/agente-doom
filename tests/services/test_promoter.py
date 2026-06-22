from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.services.promoter import promote_checkpoint
from doom_agent.utils.checkpoints import (
    build_checkpoint_metadata,
    checkpoint_zip_path,
    load_checkpoint_metadata,
    promoted_checkpoint_stem,
    save_checkpoint_bundle,
)


class DummyModel:
    def save(self, checkpoint_stem: str) -> None:
        checkpoint_zip_path(Path(checkpoint_stem)).write_text("dummy model", encoding="utf-8")


class PromoterTests(unittest.TestCase):
    def test_promote_checkpoint_copies_source_and_updates_metadata(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "promoter"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        project_paths.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        project_paths.auto_checkpoints_dir.mkdir(parents=True, exist_ok=True)
        profile = get_training_profile("default")
        source_checkpoint_stem = (
            project_paths.auto_checkpoints_dir / f"{profile.checkpoint_name}_1250000_steps"
        )
        promoted_checkpoint_path = (
            project_paths.checkpoints_dir
            / promoted_checkpoint_stem(Path(profile.checkpoint_name)).with_suffix(".zip").name
        )

        save_checkpoint_bundle(
            DummyModel(),
            source_checkpoint_stem,
            build_checkpoint_metadata(
                "default",
                profile,
                saved_timesteps=1250000,
                training_status="periodic_checkpoint",
                checkpoint_role="auto",
                evaluation_source="training_internal",
                canonical_checkpoint_path=str(source_checkpoint_stem.with_suffix(".zip")),
                evaluation_metrics={
                    "mean_reward": -8.2,
                    "std_reward": 9.0,
                    "mean_episode_length": 10.2,
                    "episodes": 20,
                },
            ),
        )

        try:
            with (
                patch(
                    "doom_agent.services.promoter.build_project_paths",
                    return_value=project_paths,
                ),
                patch(
                    "doom_agent.services.promoter.evaluate",
                    return_value={
                        "checkpoint_path": str(source_checkpoint_stem.with_suffix(".zip")),
                        "scenario_key": "basic",
                        "scenario_name": "basic.cfg",
                        "deterministic": True,
                        "render": False,
                        "metrics": {
                            "mean_reward": -7.9,
                            "std_reward": 8.1,
                            "mean_episode_length": 9.8,
                            "episodes": 50,
                        },
                    },
                ),
            ):
                result = promote_checkpoint(
                    checkpoint_name=str(source_checkpoint_stem.with_suffix(".zip")),
                    episodes=50,
                )

            self.assertEqual(result.promoted_checkpoint_path, promoted_checkpoint_path)
            self.assertTrue(promoted_checkpoint_path.exists())
            promoted_metadata = load_checkpoint_metadata(promoted_checkpoint_path.with_suffix(""))
            self.assertIsNotNone(promoted_metadata)
            assert promoted_metadata is not None
            self.assertEqual(promoted_metadata["checkpoint_role"], "promoted")
            self.assertEqual(promoted_metadata["evaluation_source"], "offline_cli")
            self.assertEqual(
                promoted_metadata["canonical_checkpoint_path"],
                str(source_checkpoint_stem.with_suffix(".zip")),
            )
            self.assertIsNotNone(promoted_metadata["evaluation_metrics"])
            assert promoted_metadata["evaluation_metrics"] is not None
            self.assertEqual(
                promoted_metadata["evaluation_metrics"]["episodes"],
                50,
            )
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)
