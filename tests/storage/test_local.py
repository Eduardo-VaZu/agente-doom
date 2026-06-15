from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths
from doom_agent.storage import build_run_artifact_paths


class LocalStorageTests(unittest.TestCase):
    def test_run_artifact_paths_are_namespaced_by_run_id(self) -> None:
        project_paths = build_project_paths(root_dir=Path("artifacts") / "test-temp" / "storage")
        run_artifacts = build_run_artifact_paths(project_paths, "foundation__20260101T000000000000Z")

        self.assertEqual(
            run_artifacts.run_dir,
            project_paths.runs_dir / "foundation__20260101T000000000000Z",
        )
        self.assertEqual(run_artifacts.report_path, run_artifacts.run_dir / "report.json")
        self.assertEqual(run_artifacts.videos_dir, run_artifacts.run_dir / "videos")
        self.assertEqual(run_artifacts.tensorboard_dir, run_artifacts.run_dir / "tensorboard")
