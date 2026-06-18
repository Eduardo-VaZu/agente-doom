from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.persistence.repositories import TrainingRunRepository


class DummyScalarResult:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def __iter__(self) -> Any:
        return iter(self._values)


class DummySession:
    def __init__(self, values: list[str]) -> None:
        self._values = values
        self.closed = False

    def scalars(self, statement: object) -> DummyScalarResult:
        _ = statement
        return DummyScalarResult(self._values)

    def close(self) -> None:
        self.closed = True


class SyncRepositoryTests(unittest.TestCase):
    def test_list_run_ids_by_sync_status_returns_ordered_run_ids(self) -> None:
        session = DummySession(["run-2", "run-1"])
        repository = TrainingRunRepository(session_factory=cast(Any, lambda: session))

        run_ids = repository.list_run_ids_by_sync_status(sync_status="local_only", limit=2)

        self.assertEqual(run_ids, ["run-2", "run-1"])
        self.assertTrue(session.closed)
