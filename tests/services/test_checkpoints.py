from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.services.trainer import (
    TrainingExecutionResult,
    copy_run_best_checkpoint_if_updated,
    select_resume_checkpoint_path,
)
from doom_agent.shared.contracts import CheckpointMetadataPayload, EvaluationMetricsPayload
from doom_agent.utils.checkpoints import (
    active_checkpoint_stem,
    build_checkpoint_metadata,
    checkpoint_metadata_path,
    checkpoint_zip_path,
    copy_checkpoint_bundle,
    load_checkpoint_metadata,
    promoted_checkpoint_stem,
    resolve_checkpoint_preference,
    resolve_latest_checkpoint,
    resolve_resume_checkpoint,
    save_checkpoint_bundle,
)


class DummyModel:
    def save(self, checkpoint_stem: str) -> None:
        checkpoint_zip_path(Path(checkpoint_stem)).write_text("dummy model", encoding="utf-8")


class CheckpointTests(unittest.TestCase):
    def test_save_checkpoint_bundle_creates_zip_and_metadata(self) -> None:
        profile = get_training_profile("default", requested_timesteps=8)
        metadata = build_checkpoint_metadata(
            "default",
            profile,
            saved_timesteps=profile.effective_timesteps,
            run_id="run-1",
            resume_source="artifacts/checkpoints/previous.zip",
            resume_saved_timesteps=10240,
            training_status="completed",
            checkpoint_role="final",
            evaluation_source="training_internal",
            canonical_checkpoint_path=str(
                Path("artifacts")
                / "test-temp"
                / "checkpoint-bundle"
                / "ppo_doom_recurrent_default.zip"
            ),
            evaluation_metrics=EvaluationMetricsPayload(
                mean_reward=12.5,
                std_reward=0.5,
                mean_episode_length=42.0,
                episodes=3,
            ),
        )

        temp_dir = Path("artifacts") / "test-temp" / "checkpoint-bundle"
        shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            checkpoint_stem = temp_dir / "ppo_doom_recurrent_default"
            save_checkpoint_bundle(DummyModel(), checkpoint_stem, metadata)

            self.assertTrue(checkpoint_zip_path(checkpoint_stem).exists())
            self.assertTrue(checkpoint_metadata_path(checkpoint_stem).exists())

            loaded_metadata = load_checkpoint_metadata(checkpoint_stem)
            self.assertIsNotNone(loaded_metadata)
            loaded_metadata = cast(CheckpointMetadataPayload, loaded_metadata)
            self.assertEqual(loaded_metadata["profile_name"], "default")
            self.assertEqual(loaded_metadata["run_id"], "run-1")
            self.assertEqual(loaded_metadata["saved_timesteps"], 2048)
            self.assertEqual(loaded_metadata["resume_saved_timesteps"], 10240)
            self.assertEqual(loaded_metadata["training_status"], "completed")
            self.assertEqual(loaded_metadata["checkpoint_role"], "final")
            self.assertEqual(loaded_metadata["evaluation_source"], "training_internal")
            evaluation_metrics = cast(
                EvaluationMetricsPayload, loaded_metadata["evaluation_metrics"]
            )
            self.assertEqual(evaluation_metrics["mean_reward"], 12.5)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_copy_checkpoint_bundle_retries_on_transient_permission_error(self) -> None:
        """Regresion: Windows Defender/Search Indexer pueden retener brevemente el zip
        recien escrito, causando PermissionError [WinError 32]. copy_checkpoint_bundle
        debe reintentar en vez de tumbar el entrenamiento completo."""
        temp_dir = Path("artifacts") / "test-temp" / "checkpoint-bundle-retry"
        shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            profile = get_training_profile("default", requested_timesteps=8)
            source_stem = temp_dir / "source"
            target_stem = temp_dir / "target"
            save_checkpoint_bundle(
                DummyModel(),
                source_stem,
                build_checkpoint_metadata("default", profile, saved_timesteps=1000),
            )

            real_copy2 = shutil.copy2
            call_count = {"n": 0}

            def flaky_copy2(src: str, dst: str) -> str:
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise PermissionError(
                        "[WinError 32] El proceso no tiene acceso al archivo "
                        "porque esta siendo utilizado por otro proceso"
                    )
                return real_copy2(src, dst)

            with patch("doom_agent.utils.checkpoints.shutil.copy2", side_effect=flaky_copy2):
                copy_checkpoint_bundle(source_stem, target_stem)

            self.assertTrue(checkpoint_zip_path(target_stem).exists())
            self.assertGreaterEqual(call_count["n"], 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_resolve_latest_checkpoint_prefers_highest_timestep(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "resume-selection"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        project_paths.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        project_paths.auto_checkpoints_dir.mkdir(parents=True, exist_ok=True)

        profile = get_training_profile("default")
        final_checkpoint = project_paths.checkpoints_dir / profile.checkpoint_name
        auto_checkpoint = (
            project_paths.auto_checkpoints_dir / f"{profile.checkpoint_name}_12000_steps"
        )

        try:
            save_checkpoint_bundle(
                DummyModel(),
                final_checkpoint,
                build_checkpoint_metadata("default", profile, saved_timesteps=10000),
            )
            save_checkpoint_bundle(
                DummyModel(),
                auto_checkpoint,
                build_checkpoint_metadata("default", profile, saved_timesteps=12000),
            )

            resolved = resolve_latest_checkpoint(project_paths, profile.checkpoint_name)
            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertEqual(resolved.checkpoint_stem, auto_checkpoint)
            self.assertEqual(resolved.saved_timesteps, 12000)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_resolve_checkpoint_preference_prefers_best_checkpoint(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "best-selection"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        project_paths.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        profile = get_training_profile("default")
        final_checkpoint = project_paths.checkpoints_dir / profile.checkpoint_name
        best_checkpoint = project_paths.checkpoints_dir / f"{profile.checkpoint_name}_best"

        try:
            save_checkpoint_bundle(
                DummyModel(),
                final_checkpoint,
                build_checkpoint_metadata("default", profile, saved_timesteps=10000),
            )
            save_checkpoint_bundle(
                DummyModel(),
                best_checkpoint,
                build_checkpoint_metadata(
                    "default",
                    profile,
                    saved_timesteps=9000,
                    training_status="best_model",
                    is_best_checkpoint=True,
                ),
            )

            resolved = resolve_checkpoint_preference(
                project_paths,
                profile.checkpoint_name,
                preference="best",
            )
            self.assertEqual(resolved.checkpoint_stem, best_checkpoint)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_resolve_checkpoint_preference_prefers_promoted_checkpoint(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "promoted-selection"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        project_paths.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        profile = get_training_profile("default")
        final_checkpoint = project_paths.checkpoints_dir / profile.checkpoint_name
        promoted_checkpoint = (
            project_paths.checkpoints_dir / promoted_checkpoint_stem(final_checkpoint).name
        )
        best_checkpoint = project_paths.checkpoints_dir / f"{profile.checkpoint_name}_best"

        try:
            save_checkpoint_bundle(
                DummyModel(),
                final_checkpoint,
                build_checkpoint_metadata("default", profile, saved_timesteps=10000),
            )
            save_checkpoint_bundle(
                DummyModel(),
                best_checkpoint,
                build_checkpoint_metadata(
                    "default",
                    profile,
                    saved_timesteps=11000,
                    training_status="best_model",
                    is_best_checkpoint=True,
                ),
            )
            save_checkpoint_bundle(
                DummyModel(),
                promoted_checkpoint,
                build_checkpoint_metadata(
                    "default",
                    profile,
                    saved_timesteps=9000,
                    training_status="promoted_checkpoint",
                    checkpoint_role="promoted",
                    evaluation_source="offline_cli",
                    is_best_checkpoint=True,
                ),
            )

            resolved = resolve_checkpoint_preference(
                project_paths,
                profile.checkpoint_name,
                preference="best",
            )
            self.assertEqual(resolved.checkpoint_stem, promoted_checkpoint)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_resolve_latest_checkpoint_prefers_promoted_checkpoint(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "promoted-latest-selection"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        project_paths.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        project_paths.auto_checkpoints_dir.mkdir(parents=True, exist_ok=True)

        profile = get_training_profile("default")
        final_checkpoint = project_paths.checkpoints_dir / profile.checkpoint_name
        auto_checkpoint = (
            project_paths.auto_checkpoints_dir / f"{profile.checkpoint_name}_12000_steps"
        )
        promoted_checkpoint = (
            project_paths.checkpoints_dir / promoted_checkpoint_stem(final_checkpoint).name
        )

        try:
            save_checkpoint_bundle(
                DummyModel(),
                auto_checkpoint,
                build_checkpoint_metadata("default", profile, saved_timesteps=12000),
            )
            save_checkpoint_bundle(
                DummyModel(),
                promoted_checkpoint,
                build_checkpoint_metadata(
                    "default",
                    profile,
                    saved_timesteps=9000,
                    training_status="promoted_checkpoint",
                    checkpoint_role="promoted",
                    evaluation_source="offline_cli",
                    is_best_checkpoint=True,
                ),
            )

            resolved = resolve_latest_checkpoint(project_paths, profile.checkpoint_name)
            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertEqual(resolved.checkpoint_stem, promoted_checkpoint)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_resolve_resume_checkpoint_prefers_active_checkpoint(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "active-resume-selection"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        project_paths.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        project_paths.auto_checkpoints_dir.mkdir(parents=True, exist_ok=True)

        profile = get_training_profile("default")
        final_checkpoint = project_paths.checkpoints_dir / profile.checkpoint_name
        promoted_checkpoint = (
            project_paths.checkpoints_dir / promoted_checkpoint_stem(final_checkpoint).name
        )
        active_checkpoint = (
            project_paths.checkpoints_dir / active_checkpoint_stem(final_checkpoint).name
        )

        try:
            save_checkpoint_bundle(
                DummyModel(),
                promoted_checkpoint,
                build_checkpoint_metadata(
                    "default",
                    profile,
                    saved_timesteps=9000,
                    training_status="promoted_checkpoint",
                    checkpoint_role="promoted",
                    evaluation_source="offline_cli",
                    is_best_checkpoint=True,
                ),
            )
            save_checkpoint_bundle(
                DummyModel(),
                active_checkpoint,
                build_checkpoint_metadata(
                    "default",
                    profile,
                    saved_timesteps=11000,
                    training_status="active_checkpoint",
                    checkpoint_role="active",
                    evaluation_source="workspace_handoff",
                ),
            )

            resolved = resolve_resume_checkpoint(project_paths, profile.checkpoint_name)
            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertEqual(resolved.checkpoint_stem, active_checkpoint)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_select_resume_checkpoint_path_prefers_best_checkpoint_when_available(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "resume-best-selection"
        shutil.rmtree(root_dir, ignore_errors=True)
        checkpoint_dir = root_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        final_checkpoint_path = checkpoint_dir / "stage.zip"
        best_checkpoint_path = checkpoint_dir / "stage_best.zip"
        final_checkpoint_path.write_text("final", encoding="utf-8")
        best_checkpoint_path.write_text("best", encoding="utf-8")

        try:
            result = TrainingExecutionResult(
                profile_name="default",
                profile=get_training_profile("default"),
                final_checkpoint_path=final_checkpoint_path,
                best_checkpoint_path=best_checkpoint_path,
                report_path=root_dir / "report.json",
                training_status="completed",
                completed=True,
                saved_timesteps=1000,
                stopped_early=False,
                stop_reason=None,
            )

            self.assertEqual(select_resume_checkpoint_path(result), best_checkpoint_path)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_copy_run_best_checkpoint_if_updated_skips_legacy_best_checkpoint(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "skip-legacy-best-checkpoint"
        shutil.rmtree(root_dir, ignore_errors=True)
        checkpoint_dir = root_dir / "checkpoints"
        run_checkpoint_dir = root_dir / "run-checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        run_checkpoint_dir.mkdir(parents=True, exist_ok=True)

        run_best_checkpoint_stem = run_checkpoint_dir / "best_model"
        official_best_checkpoint_stem = checkpoint_dir / "stage_best"

        checkpoint_zip_path(run_best_checkpoint_stem).write_text("best", encoding="utf-8")
        checkpoint_metadata_path(run_best_checkpoint_stem).write_text("{}", encoding="utf-8")

        try:
            copied_path = copy_run_best_checkpoint_if_updated(
                run_best_checkpoint_stem,
                official_best_checkpoint_stem,
                best_checkpoint_updated=False,
            )

            self.assertIsNone(copied_path)
            self.assertFalse(checkpoint_zip_path(official_best_checkpoint_stem).exists())
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_copy_run_best_checkpoint_if_updated_syncs_official_alias(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "sync-official-best-checkpoint"
        shutil.rmtree(root_dir, ignore_errors=True)
        checkpoint_dir = root_dir / "checkpoints"
        run_checkpoint_dir = root_dir / "run-checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        run_checkpoint_dir.mkdir(parents=True, exist_ok=True)

        run_best_checkpoint_stem = run_checkpoint_dir / "best_model"
        official_best_checkpoint_stem = checkpoint_dir / "stage_best"
        checkpoint_zip_path(run_best_checkpoint_stem).write_text("best", encoding="utf-8")
        checkpoint_metadata_path(run_best_checkpoint_stem).write_text(
            '{"canonical_checkpoint_path":"run-checkpoints/best_model.zip"}',
            encoding="utf-8",
        )

        try:
            copied_path = copy_run_best_checkpoint_if_updated(
                run_best_checkpoint_stem,
                official_best_checkpoint_stem,
                best_checkpoint_updated=True,
            )

            self.assertEqual(copied_path, checkpoint_zip_path(run_best_checkpoint_stem))
            self.assertTrue(checkpoint_zip_path(official_best_checkpoint_stem).exists())
            self.assertTrue(checkpoint_metadata_path(official_best_checkpoint_stem).exists())
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)
