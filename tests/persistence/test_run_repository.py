from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.persistence.repositories import TrainingRunRepository, build_run_artifact_records
from doom_agent.shared.contracts import EvaluationMetricsPayload, TrainingRunReportPayload
from doom_agent.storage import build_run_artifact_paths
from doom_agent.utils.reports import build_run_id, build_training_run_report


class DummySession:
    def __init__(self) -> None:
        self.runs: dict[str, Any] = {}
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def get(self, model: type[object], run_id: str) -> object | None:
        _ = model
        return self.runs.get(run_id)

    def add(self, training_run: Any) -> None:
        run_id = training_run.run_id
        self.runs[run_id] = training_run

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class TrainingRunRepositoryTests(unittest.TestCase):
    def test_build_run_artifact_records_includes_report_and_checkpoints(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "run-repository-artifacts"
        shutil.rmtree(root_dir, ignore_errors=True)
        report, report_path = _build_report_fixture(root_dir)

        try:
            records = build_run_artifact_records(report, report_path=report_path)
            self.assertEqual(len(records), 4)
            self.assertEqual(records[0].artifact_type, "report")
            self.assertEqual(records[1].artifact_role, "final")
            self.assertEqual(records[2].artifact_role, "best")
            self.assertEqual(records[3].artifact_type, "video")
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_upsert_run_report_stores_run_and_artifacts(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "run-repository-upsert"
        shutil.rmtree(root_dir, ignore_errors=True)
        report, report_path = _build_report_fixture(root_dir)
        session = DummySession()
        repository = TrainingRunRepository(session_factory=_build_session_factory(session))

        try:
            repository.upsert_run_report(report, report_path=report_path)

            self.assertTrue(session.committed)
            self.assertTrue(session.closed)
            persisted_run = session.runs[report["run_id"]]
            self.assertEqual(persisted_run.mean_reward, 10.0)
            self.assertEqual(persisted_run.local_report_path, str(report_path))
            self.assertEqual(len(persisted_run.artifacts), 4)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)


def _build_session_factory(session: DummySession) -> Any:
    def factory() -> DummySession:
        return session

    return factory


def _build_report_fixture(root_dir: Path) -> tuple[TrainingRunReportPayload, Path]:
    project_paths = build_project_paths(root_dir=root_dir)
    profile = get_training_profile("default", seed=123)
    run_id = build_run_id(profile)
    run_artifacts = build_run_artifact_paths(project_paths, run_id)
    run_artifacts.run_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts.videos_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts.tensorboard_dir.mkdir(parents=True, exist_ok=True)

    final_checkpoint_path = run_artifacts.final_checkpoint_stem.with_suffix(".zip")
    final_checkpoint_path.write_text("final", encoding="utf-8")
    final_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")

    best_checkpoint_path = run_artifacts.best_checkpoint_stem.with_suffix(".zip")
    best_checkpoint_path.write_text("best", encoding="utf-8")
    best_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")
    (run_artifacts.videos_dir / "doom_foundation_agent-step-0-to-step-1500.mp4").write_text(
        "video",
        encoding="utf-8",
    )

    report = build_training_run_report(
        run_id=run_id,
        created_at_utc="2026-01-01T00:00:00+00:00",
        profile_name="default",
        run_label="manual:test",
        profile=profile,
        run_artifacts=run_artifacts,
        checkpoint_path=project_paths.checkpoints_dir / f"{profile.checkpoint_name}.zip",
        best_checkpoint_path=project_paths.checkpoints_dir / f"{profile.checkpoint_name}_best.zip",
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
    report_path = run_artifacts.report_path
    report_path.write_text("{}", encoding="utf-8")
    return report, report_path
