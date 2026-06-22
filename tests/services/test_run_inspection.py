from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.services.run_inspection import inspect_run
from doom_agent.shared.contracts import EvaluationMetricsPayload
from doom_agent.storage import RunArtifactPaths, build_run_artifact_paths
from doom_agent.utils.filesystem import write_json
from doom_agent.utils.manifests import build_run_manifest, save_run_manifest
from doom_agent.utils.reports import (
    build_run_id,
    build_training_run_report,
    save_training_run_report,
)


class RunInspectionTests(unittest.TestCase):
    def test_inspect_run_reads_report_and_manifest_summary(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "run-inspection"
        shutil.rmtree(root_dir, ignore_errors=True)
        run_id, run_artifacts = _build_run_fixture(root_dir)

        try:
            with patch(
                "doom_agent.services.run_inspection.has_explicit_database_url",
                return_value=False,
            ):
                inspection = inspect_run(run_id, root_dir=root_dir)

            self.assertEqual(inspection["run_id"], run_id)
            self.assertTrue(inspection["manifest_exists"])
            self.assertTrue(inspection["checkpoint_archive_exists"])
            self.assertTrue(inspection["best_checkpoint_archive_exists"])
            self.assertEqual(inspection["selected_auto_checkpoint_count"], 1)
            self.assertIn("report.json", inspection["remote_sync_candidates"])
            self.assertIn("manifest.json", inspection["remote_sync_candidates"])
            self.assertIn(
                "checkpoints/auto/doom_foundation_agent_50000_steps.zip",
                inspection["remote_sync_candidates"],
            )
            self.assertTrue(inspection["handoff_ready"])
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_inspect_run_normalizes_legacy_report_without_manifest_fields(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "run-inspection-legacy"
        shutil.rmtree(root_dir, ignore_errors=True)
        run_id, run_artifacts = _build_run_fixture(root_dir)

        try:
            report_path = run_artifacts.report_path
            legacy_report = json.loads(report_path.read_text(encoding="utf-8"))
            legacy_report.pop("manifest_path", None)
            legacy_report.pop("selected_auto_checkpoint_archive_paths", None)
            legacy_report.pop("evaluation_history", None)
            write_json(report_path, legacy_report)
            if run_artifacts.manifest_path.exists():
                run_artifacts.manifest_path.unlink()

            with patch(
                "doom_agent.services.run_inspection.has_explicit_database_url",
                return_value=False,
            ):
                inspection = inspect_run(run_id, root_dir=root_dir)

            self.assertFalse(inspection["manifest_exists"])
            self.assertEqual(
                inspection["manifest_path"],
                str(run_artifacts.run_dir / "manifest.json"),
            )
            self.assertEqual(inspection["selected_auto_checkpoint_count"], 0)
            self.assertEqual(inspection["evaluation_history_count"], 0)
            self.assertEqual(inspection["remote_sync_candidates"], [])
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)


def _build_run_fixture(root_dir: Path) -> tuple[str, RunArtifactPaths]:
    project_paths = build_project_paths(root_dir=root_dir)
    profile = get_training_profile("default", seed=123)
    run_id = build_run_id(profile)
    run_artifacts = build_run_artifact_paths(project_paths, run_id)
    run_artifacts.run_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts.auto_checkpoints_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts.videos_dir.mkdir(parents=True, exist_ok=True)

    final_checkpoint_path = run_artifacts.final_checkpoint_stem.with_suffix(".zip")
    final_checkpoint_path.write_text("final", encoding="utf-8")
    final_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")

    best_checkpoint_path = run_artifacts.best_checkpoint_stem.with_suffix(".zip")
    best_checkpoint_path.write_text("best", encoding="utf-8")
    best_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")

    selected_auto_checkpoint_path = (
        run_artifacts.auto_checkpoints_dir / f"{profile.checkpoint_name}_50000_steps.zip"
    )
    selected_auto_checkpoint_path.write_text("auto", encoding="utf-8")
    selected_auto_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")

    report = build_training_run_report(
        run_id=run_id,
        created_at_utc="2026-01-01T00:00:00+00:00",
        profile_name="default",
        run_label="manual:test",
        profile=profile,
        run_artifacts=run_artifacts,
        checkpoint_path=final_checkpoint_path,
        best_checkpoint_path=best_checkpoint_path,
        selected_auto_checkpoint_paths=[selected_auto_checkpoint_path],
        official_checkpoint_path=project_paths.checkpoints_dir / f"{profile.checkpoint_name}.zip",
        official_best_checkpoint_path=project_paths.checkpoints_dir
        / f"{profile.checkpoint_name}_best.zip",
        training_status="completed",
        completed=True,
        saved_timesteps=profile.effective_timesteps,
        resume_mode="auto",
        resume_source=None,
        resume_saved_timesteps=None,
        evaluation_metrics=EvaluationMetricsPayload(
            mean_reward=10.0,
            std_reward=1.0,
            mean_episode_length=30.0,
            episodes=5,
        ),
        duration_seconds=12.5,
        stopped_early=False,
        stop_reason=None,
    )
    report_path = save_training_run_report(project_paths, report)
    manifest = build_run_manifest(
        report,
        run_artifacts=run_artifacts,
        report_path=report_path,
    )
    save_run_manifest(run_artifacts, manifest)
    return run_id, run_artifacts
