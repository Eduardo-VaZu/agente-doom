from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.persistence import Base


class PersistenceModelTests(unittest.TestCase):
    def test_expected_tables_are_registered(self) -> None:
        self.assertEqual(
            set(Base.metadata.tables),
            {"training_runs", "run_artifacts", "sync_events"},
        )

    def test_run_artifacts_remote_uri_is_unique(self) -> None:
        run_artifacts = Base.metadata.tables["run_artifacts"]
        unique_constraint_names = {
            constraint.name
            for constraint in run_artifacts.constraints
            if getattr(constraint, "name", None) is not None
        }
        self.assertIn("uq_run_artifacts_remote_uri", unique_constraint_names)
