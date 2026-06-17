from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.persistence.repositories import SyncCandidateArtifact
from doom_agent.services.sync import ArtifactSyncService
from doom_agent.storage.remote import RemoteArtifactLocation


class FakeArtifactStore:
    def __init__(self, *, fail: bool = False, storage_backend: str = "minio") -> None:
        self.fail = fail
        self.object_prefix = "runs"
        self.storage_backend = storage_backend
        self.upload_calls: list[tuple[Path, str, str | None]] = []

    def upload_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: str | None = None,
    ) -> RemoteArtifactLocation:
        self.upload_calls.append((local_path, object_key, content_type))
        if self.fail:
            raise RuntimeError("upload failed")
        return RemoteArtifactLocation(
            storage_backend=self.storage_backend,
            bucket_name="agente-doom-artifacts",
            object_key=object_key,
            remote_uri=f"{self.storage_backend}://agente-doom-artifacts/{object_key}",
            etag="etag-1",
        )


class FakeSyncRepository:
    def __init__(self, candidates: list[SyncCandidateArtifact]) -> None:
        self._candidates = candidates
        self.pending_run_ids: list[str] = []
        self.pending_artifacts: list[int] = []
        self.synced_artifacts: list[tuple[int, str, str, str, str]] = []
        self.failed_artifacts: list[tuple[int, str]] = []
        self.updated_run_statuses: list[tuple[str, str]] = []
        self.started_events: list[tuple[str, int, str, dict[str, object] | None]] = []
        self.succeeded_events: list[tuple[int, dict[str, object] | None]] = []
        self.failed_events: list[tuple[int, str, dict[str, object] | None]] = []
        self._next_event_id = 1

    def list_sync_candidates(self, run_id: str) -> list[SyncCandidateArtifact]:
        return [candidate for candidate in self._candidates if candidate.run_id == run_id]

    def mark_run_sync_pending(self, run_id: str) -> None:
        self.pending_run_ids.append(run_id)

    def update_run_sync_status(self, run_id: str, sync_status: str) -> None:
        self.updated_run_statuses.append((run_id, sync_status))

    def mark_artifact_sync_pending(self, artifact_id: int) -> None:
        self.pending_artifacts.append(artifact_id)

    def mark_artifact_synced(
        self,
        artifact_id: int,
        *,
        storage_backend: str,
        bucket_name: str,
        object_key: str,
        remote_uri: str,
    ) -> None:
        self.synced_artifacts.append(
            (
                artifact_id,
                storage_backend,
                bucket_name,
                object_key,
                remote_uri,
            )
        )

    def mark_artifact_failed(self, artifact_id: int, error_message: str) -> None:
        self.failed_artifacts.append((artifact_id, error_message))

    def create_sync_event_start(
        self,
        *,
        run_id: str,
        artifact_id: int,
        operation: str,
        details_json: dict[str, object] | None = None,
    ) -> int:
        event_id = self._next_event_id
        self._next_event_id += 1
        self.started_events.append((run_id, artifact_id, operation, details_json))
        return event_id

    def mark_sync_event_succeeded(
        self,
        event_id: int,
        *,
        details_json: dict[str, object] | None = None,
    ) -> None:
        self.succeeded_events.append((event_id, details_json))

    def mark_sync_event_failed(
        self,
        event_id: int,
        *,
        error_message: str,
        details_json: dict[str, object] | None = None,
    ) -> None:
        self.failed_events.append((event_id, error_message, details_json))


class ArtifactSyncServiceTests(unittest.TestCase):
    def test_sync_run_uploads_checkpoint_and_marks_run_synced(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "sync-service-success"
        shutil.rmtree(root_dir, ignore_errors=True)
        checkpoint_dir = root_dir / "run" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / "final_model.zip"
        checkpoint_path.write_text("checkpoint", encoding="utf-8")

        candidate = SyncCandidateArtifact(
            artifact_id=1,
            run_id="run-1",
            artifact_type="checkpoint",
            artifact_role="final",
            local_path=checkpoint_path,
            run_local_dir=root_dir / "run",
        )
        repository = FakeSyncRepository([candidate])
        artifact_store = FakeArtifactStore()

        try:
            result = ArtifactSyncService(
                repository=repository,
                artifact_store=artifact_store,
                object_prefix="runs",
            ).sync_run("run-1")

            self.assertEqual(result.synced_count, 1)
            self.assertEqual(result.failed_count, 0)
            self.assertEqual(result.final_status, "synced")
            self.assertEqual(
                artifact_store.upload_calls[0][1],
                "runs/run-1/checkpoints/final_model.zip",
            )
            self.assertEqual(repository.updated_run_statuses[-1], ("run-1", "synced"))
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_sync_run_marks_artifact_and_run_failed_when_upload_fails(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "sync-service-failure"
        shutil.rmtree(root_dir, ignore_errors=True)
        checkpoint_dir = root_dir / "run" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / "final_model.zip"
        checkpoint_path.write_text("checkpoint", encoding="utf-8")

        candidate = SyncCandidateArtifact(
            artifact_id=7,
            run_id="run-2",
            artifact_type="checkpoint",
            artifact_role="final",
            local_path=checkpoint_path,
            run_local_dir=root_dir / "run",
        )
        repository = FakeSyncRepository([candidate])
        artifact_store = FakeArtifactStore(fail=True)

        try:
            result = ArtifactSyncService(
                repository=repository,
                artifact_store=artifact_store,
                object_prefix="runs",
            ).sync_run("run-2")

            self.assertEqual(result.synced_count, 0)
            self.assertEqual(result.failed_count, 1)
            self.assertEqual(result.final_status, "failed")
            self.assertEqual(repository.failed_artifacts[0][0], 7)
            self.assertEqual(repository.updated_run_statuses[-1], ("run-2", "failed"))
            self.assertEqual(len(repository.failed_events), 1)
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)
