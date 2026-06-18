from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from doom_agent.persistence.enums import SyncOperation, SyncStatus
from doom_agent.persistence.repositories import SyncCandidateArtifact, TrainingRunRepository
from doom_agent.storage import (
    DEFAULT_OBJECT_PREFIX,
    ArtifactStore,
    MinioArtifactStore,
    S3ArtifactStore,
    build_remote_object_key,
    get_storage_backend,
    guess_content_type,
)


@dataclass(frozen=True, slots=True)
class SyncRunResult:
    run_id: str
    attempted_count: int
    synced_count: int
    failed_count: int
    final_status: str


@dataclass(frozen=True, slots=True)
class SyncArtifactPreview:
    artifact_id: int
    artifact_type: str
    artifact_role: str | None
    local_path: str
    object_key: str


@dataclass(frozen=True, slots=True)
class SyncRunPreview:
    run_id: str
    storage_backend: str
    candidates: list[SyncArtifactPreview]


class SyncRepository(Protocol):
    def list_sync_candidates(self, run_id: str) -> list[SyncCandidateArtifact]: ...

    def mark_run_sync_pending(self, run_id: str) -> None: ...

    def update_run_sync_status(self, run_id: str, sync_status: str) -> None: ...

    def mark_artifact_sync_pending(self, artifact_id: int) -> None: ...

    def mark_artifact_synced(
        self,
        artifact_id: int,
        *,
        storage_backend: str,
        bucket_name: str,
        object_key: str,
        remote_uri: str,
    ) -> None: ...

    def mark_artifact_failed(self, artifact_id: int, error_message: str) -> None: ...

    def create_sync_event_start(
        self,
        *,
        run_id: str,
        artifact_id: int,
        operation: str,
        details_json: dict[str, object] | None = None,
    ) -> int: ...

    def mark_sync_event_succeeded(
        self,
        event_id: int,
        *,
        details_json: dict[str, object] | None = None,
    ) -> None: ...

    def mark_sync_event_failed(
        self,
        event_id: int,
        *,
        error_message: str,
        details_json: dict[str, object] | None = None,
    ) -> None: ...


class ArtifactSyncService:
    def __init__(
        self,
        repository: SyncRepository | None = None,
        *,
        artifact_store: ArtifactStore | None = None,
        object_prefix: str | None = None,
    ) -> None:
        self._repository = repository or TrainingRunRepository()
        configured_artifact_store = artifact_store or _build_default_artifact_store()
        self._artifact_store = configured_artifact_store
        if object_prefix is not None:
            normalized_prefix = object_prefix.strip("/")
            self._object_prefix = normalized_prefix or DEFAULT_OBJECT_PREFIX
        elif isinstance(configured_artifact_store, (MinioArtifactStore, S3ArtifactStore)):
            self._object_prefix = configured_artifact_store.object_prefix
        else:
            self._object_prefix = DEFAULT_OBJECT_PREFIX

    def describe_run_sync(self, run_id: str) -> SyncRunPreview:
        candidates = self._repository.list_sync_candidates(run_id)
        return SyncRunPreview(
            run_id=run_id,
            storage_backend=_resolve_storage_backend_name(self._artifact_store),
            candidates=[
                SyncArtifactPreview(
                    artifact_id=candidate.artifact_id,
                    artifact_type=candidate.artifact_type,
                    artifact_role=candidate.artifact_role,
                    local_path=str(candidate.local_path),
                    object_key=self._build_object_key(candidate),
                )
                for candidate in candidates
            ],
        )

    def sync_run(self, run_id: str) -> SyncRunResult:
        candidates = self._repository.list_sync_candidates(run_id)
        if not candidates:
            return SyncRunResult(
                run_id=run_id,
                attempted_count=0,
                synced_count=0,
                failed_count=0,
                final_status=SyncStatus.LOCAL_ONLY.value,
            )

        self._repository.mark_run_sync_pending(run_id)
        attempted_count = 0
        synced_count = 0
        failed_count = 0

        for candidate in candidates:
            attempted_count += 1
            if self._sync_artifact(candidate):
                synced_count += 1
            else:
                failed_count += 1

        final_status = SyncStatus.SYNCED.value
        if failed_count > 0:
            final_status = SyncStatus.FAILED.value
        self._repository.update_run_sync_status(run_id, final_status)
        return SyncRunResult(
            run_id=run_id,
            attempted_count=attempted_count,
            synced_count=synced_count,
            failed_count=failed_count,
            final_status=final_status,
        )

    def sync_runs(self, run_ids: list[str]) -> list[SyncRunResult]:
        return [self.sync_run(run_id) for run_id in run_ids]

    def _sync_artifact(self, candidate: SyncCandidateArtifact) -> bool:
        object_key = self._build_object_key(candidate)
        self._repository.mark_artifact_sync_pending(candidate.artifact_id)
        event_id = self._repository.create_sync_event_start(
            run_id=candidate.run_id,
            artifact_id=candidate.artifact_id,
            operation=SyncOperation.UPLOAD.value,
            details_json={
                "local_path": str(candidate.local_path),
                "object_key": object_key,
            },
        )

        try:
            if not candidate.local_path.exists() or not candidate.local_path.is_file():
                raise FileNotFoundError(f"Archivo local no encontrado: {candidate.local_path}")

            remote_location = self._artifact_store.upload_file(
                local_path=candidate.local_path,
                object_key=object_key,
                content_type=guess_content_type(candidate.local_path),
            )
            self._repository.mark_artifact_synced(
                candidate.artifact_id,
                storage_backend=remote_location.storage_backend,
                bucket_name=remote_location.bucket_name,
                object_key=remote_location.object_key,
                remote_uri=remote_location.remote_uri,
            )
            self._repository.mark_sync_event_succeeded(
                event_id,
                details_json={
                    "local_path": str(candidate.local_path),
                    "remote_uri": remote_location.remote_uri,
                    "bucket_name": remote_location.bucket_name,
                    "object_key": remote_location.object_key,
                    "etag": remote_location.etag,
                },
            )
            return True
        except Exception as error:
            self._repository.mark_artifact_failed(candidate.artifact_id, str(error))
            self._repository.mark_sync_event_failed(
                event_id,
                error_message=str(error),
                details_json={
                    "local_path": str(candidate.local_path),
                    "object_key": object_key,
                },
            )
            return False

    def _build_object_key(self, candidate: SyncCandidateArtifact) -> str:
        return build_remote_object_key(
            object_prefix=self._object_prefix,
            run_id=candidate.run_id,
            run_local_dir=candidate.run_local_dir,
            local_path=candidate.local_path,
            artifact_type=candidate.artifact_type,
        )


def _build_default_artifact_store() -> ArtifactStore:
    backend = get_storage_backend()
    if backend == "s3":
        return S3ArtifactStore()
    return MinioArtifactStore()


def _resolve_storage_backend_name(artifact_store: ArtifactStore) -> str:
    return str(getattr(artifact_store, "storage_backend", get_storage_backend()))
