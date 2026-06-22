from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.shared.contracts import EvaluationMetricsPayload, TrainingRunReportPayload
from doom_agent.storage import RunArtifactPaths, build_run_artifact_paths
from doom_agent.utils.manifests import MANIFEST_VERSION, build_run_manifest, save_run_manifest
from doom_agent.utils.reports import build_run_id, build_training_run_report


class ManifestTests(unittest.TestCase):
    def test_build_run_manifest_indexes_run_artifacts(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "manifest-build"
        shutil.rmtree(root_dir, ignore_errors=True)
        report, report_path, run_artifacts, selected_auto_checkpoint_path = _build_report_fixture(
            root_dir
        )

        try:
            manifest = build_run_manifest(
                report,
                run_artifacts=run_artifacts,
                report_path=report_path,
            )

            self.assertEqual(manifest["manifest_version"], MANIFEST_VERSION)
            self.assertEqual(manifest["run_id"], report["run_id"])

            artifacts = {entry["relative_path"]: entry for entry in manifest["artifacts"]}
            self.assertEqual(artifacts["report.json"]["artifact_type"], "report")
            self.assertEqual(artifacts["report.json"]["artifact_role"], "summary")
            self.assertTrue(artifacts["report.json"]["remote_sync_candidate"])

            self.assertEqual(artifacts["manifest.json"]["artifact_type"], "manifest")
            self.assertTrue(artifacts["manifest.json"]["remote_sync_candidate"])
            self.assertTrue(artifacts["manifest.json"]["exists"])

            self.assertEqual(
                artifacts["checkpoints/final_model.zip"]["artifact_role"],
                "final",
            )
            self.assertEqual(
                artifacts["checkpoints/final_model.json"]["sidecar_kind"],
                "metadata",
            )
            self.assertEqual(
                artifacts["checkpoints/best_model.zip"]["artifact_role"],
                "best",
            )
            self.assertEqual(
                artifacts["checkpoints/best_model.json"]["sidecar_kind"],
                "metadata",
            )
            self.assertTrue(
                artifacts["videos/doom_foundation_agent-step-0-to-step-1500.mp4"][
                    "remote_sync_candidate"
                ]
            )
            self.assertEqual(
                artifacts["checkpoints/auto/doom_foundation_agent_50000_steps.zip"][
                    "artifact_role"
                ],
                "auto",
            )
            self.assertTrue(
                artifacts["checkpoints/auto/doom_foundation_agent_50000_steps.zip"][
                    "remote_sync_candidate"
                ]
            )
            self.assertEqual(
                artifacts["checkpoints/auto/doom_foundation_agent_50000_steps.json"][
                    "sidecar_kind"
                ],
                "metadata",
            )
            self.assertFalse(
                artifacts["checkpoints/auto/doom_foundation_agent_25000_steps.zip"][
                    "remote_sync_candidate"
                ]
            )
            self.assertEqual(
                report["selected_auto_checkpoint_archive_paths"],
                [str(selected_auto_checkpoint_path)],
            )
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_save_run_manifest_writes_json_file(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "manifest-save"
        shutil.rmtree(root_dir, ignore_errors=True)
        report, report_path, run_artifacts, _ = _build_report_fixture(root_dir)

        try:
            manifest = build_run_manifest(
                report,
                run_artifacts=run_artifacts,
                report_path=report_path,
            )
            manifest_path = save_run_manifest(run_artifacts, manifest)

            self.assertEqual(manifest_path, run_artifacts.manifest_path)
            self.assertTrue(manifest_path.exists())
            saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_manifest["run_id"], report["run_id"])
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)


def _build_report_fixture(
    root_dir: Path,
) -> tuple[TrainingRunReportPayload, Path, RunArtifactPaths, Path]:
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

    older_auto_checkpoint_path = (
        run_artifacts.auto_checkpoints_dir / f"{profile.checkpoint_name}_25000_steps.zip"
    )
    older_auto_checkpoint_path.write_text("auto-older", encoding="utf-8")
    older_auto_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")

    selected_auto_checkpoint_path = (
        run_artifacts.auto_checkpoints_dir / f"{profile.checkpoint_name}_50000_steps.zip"
    )
    selected_auto_checkpoint_path.write_text("auto", encoding="utf-8")
    selected_auto_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")

    (run_artifacts.videos_dir / "doom_foundation_agent-step-0-to-step-1500.mp4").write_text(
        "video",
        encoding="utf-8",
    )
    report_path = run_artifacts.report_path
    report_path.write_text("{}", encoding="utf-8")

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
    return report, report_path, run_artifacts, selected_auto_checkpoint_path
