from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.shared.contracts import EvaluationMetricsPayload
from doom_agent.storage import build_run_artifact_paths
from doom_agent.utils.reports import (
    build_run_id,
    build_training_run_report,
    list_experiment_runs,
    report_path_for_run,
    save_training_run_report,
)


class ReportTests(unittest.TestCase):
    def test_save_training_run_report_updates_index(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "reports"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        profile = get_training_profile("default", seed=123)
        run_id = build_run_id(profile)
        run_artifacts = build_run_artifact_paths(project_paths, run_id)
        report = build_training_run_report(
            run_id=run_id,
            created_at_utc="2026-01-01T00:00:00+00:00",
            profile_name="default",
            run_label="manual:test",
            profile=profile,
            run_artifacts=run_artifacts,
            checkpoint_path=run_artifacts.final_checkpoint_stem.with_suffix(".zip"),
            best_checkpoint_path=run_artifacts.best_checkpoint_stem.with_suffix(".zip"),
            selected_auto_checkpoint_paths=[],
            official_checkpoint_path=project_paths.checkpoints_dir
            / f"{profile.checkpoint_name}.zip",
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
            evaluation_history=[
                {
                    "step": 25000,
                    "mean_reward": 10.0,
                    "std_reward": 1.0,
                    "mean_episode_length": 30.0,
                    "episodes": 5,
                    "top_actions": [
                        {
                            "label": "ATTACK",
                            "count": 100,
                            "percentage": 50.0,
                        }
                    ],
                }
            ],
        )

        try:
            report_path = save_training_run_report(project_paths, report)
            self.assertTrue(report_path.exists())
            self.assertEqual(report_path, report_path_for_run(project_paths, run_id))
            saved_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_report["profile"]["checkpoint_name"], profile.checkpoint_name)
            self.assertEqual(saved_report["evaluation_history"][0]["step"], 25000)
            self.assertEqual(
                saved_report["evaluation_history"][0]["top_actions"][0]["label"],
                "ATTACK",
            )

            with patch("doom_agent.utils.reports.has_explicit_database_url", return_value=False):
                runs = list_experiment_runs(project_paths)
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["run_id"], run_id)
            self.assertEqual(runs[0]["mean_reward"], 10.0)
            self.assertEqual(runs[0]["run_label"], "manual:test")
            self.assertEqual(runs[0]["seed"], 123)
            self.assertEqual(
                saved_report["run_auto_checkpoints_dir"],
                str(run_artifacts.auto_checkpoints_dir),
            )
            self.assertEqual(
                saved_report["checkpoint_path"],
                str(run_artifacts.final_checkpoint_stem.with_suffix(".zip")),
            )
            self.assertEqual(
                saved_report["official_checkpoint_path"],
                str(project_paths.checkpoints_dir / f"{profile.checkpoint_name}.zip"),
            )
            self.assertEqual(saved_report["manifest_path"], str(run_artifacts.manifest_path))
            self.assertEqual(saved_report["selected_auto_checkpoint_archive_paths"], [])
            self.assertEqual(
                runs[0]["checkpoint_archive_path"],
                str(run_artifacts.final_checkpoint_stem.with_suffix(".zip")),
            )
            self.assertEqual(report_path, run_artifacts.report_path)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_list_experiment_runs_prefers_database_when_configured(self) -> None:
        project_paths = build_project_paths(root_dir=Path("artifacts") / "test-temp" / "reports-db")
        database_runs: list[dict[str, Any]] = [
            {
                "run_id": "db-run",
                "created_at_utc": "2026-01-01T00:00:00+00:00",
                "profile_name": "default",
                "run_label": None,
                "scenario_key": "basic",
                "checkpoint_name": "doom_foundation_agent",
                "checkpoint_path": "checkpoint.zip",
                "best_checkpoint_path": None,
                "checkpoint_archive_path": "final_model.zip",
                "best_checkpoint_archive_path": None,
                "saved_timesteps": 10240,
                "training_status": "completed",
                "mean_reward": None,
                "seed": 42,
                "report_path": "report.json",
            }
        ]

        repository = _FakeRunRepository(database_runs)
        with (
            patch("doom_agent.utils.reports.has_explicit_database_url", return_value=True),
            patch("doom_agent.utils.reports.TrainingRunRepository", return_value=repository),
        ):
            runs = list_experiment_runs(project_paths)

        self.assertEqual(runs, database_runs)

    def test_list_experiment_runs_falls_back_to_local_index_when_database_fails(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "reports-db-fallback"
        shutil.rmtree(root_dir, ignore_errors=True)
        project_paths = build_project_paths(root_dir=root_dir)
        profile = get_training_profile("default", seed=123)
        run_id = build_run_id(profile)
        run_artifacts = build_run_artifact_paths(project_paths, run_id)
        report = build_training_run_report(
            run_id=run_id,
            created_at_utc="2026-01-01T00:00:00+00:00",
            profile_name="default",
            run_label=None,
            profile=profile,
            run_artifacts=run_artifacts,
            checkpoint_path=run_artifacts.final_checkpoint_stem.with_suffix(".zip"),
            best_checkpoint_path=None,
            selected_auto_checkpoint_paths=[],
            official_checkpoint_path=project_paths.checkpoints_dir
            / f"{profile.checkpoint_name}.zip",
            official_best_checkpoint_path=None,
            training_status="completed",
            completed=True,
            saved_timesteps=profile.effective_timesteps,
            resume_mode="auto",
            resume_source=None,
            resume_saved_timesteps=None,
            evaluation_metrics=None,
            duration_seconds=12.5,
            stopped_early=False,
            stop_reason=None,
        )

        try:
            save_training_run_report(project_paths, report)
            with (
                patch("doom_agent.utils.reports.has_explicit_database_url", return_value=True),
                patch(
                    "doom_agent.utils.reports.TrainingRunRepository",
                    return_value=_FailingRunRepository(),
                ),
            ):
                runs = list_experiment_runs(project_paths)

            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["run_id"], run_id)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)


class _FakeRunRepository:
    def __init__(self, runs: list[dict[str, object]]) -> None:
        self._runs = runs

    def list_run_entries(self) -> list[dict[str, object]]:
        return self._runs


class _FailingRunRepository:
    def list_run_entries(self) -> list[dict[str, object]]:
        raise RuntimeError("database unavailable")
