from __future__ import annotations

from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path, PurePosixPath
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RemoteArtifactLocation:
    storage_backend: str
    bucket_name: str
    object_key: str
    remote_uri: str
    etag: str | None = None


class ArtifactStore(Protocol):
    def upload_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: str | None = None,
    ) -> RemoteArtifactLocation: ...

    def download_file(
        self,
        *,
        object_key: str,
        local_path: Path,
    ) -> None: ...


def guess_content_type(local_path: Path) -> str | None:
    guessed_type, _ = guess_type(local_path.name)
    return guessed_type


def build_remote_object_key(
    *,
    object_prefix: str,
    run_id: str,
    run_local_dir: Path,
    local_path: Path,
    artifact_type: str,
) -> str:
    root_path = _prefix_root(object_prefix) / run_id
    try:
        relative_path = local_path.relative_to(run_local_dir)
        return str(root_path / PurePosixPath(relative_path.as_posix()))
    except ValueError:
        return str(root_path / artifact_type / local_path.name)


def _prefix_root(object_prefix: str) -> PurePosixPath:
    cleaned_prefix = object_prefix.strip("/")
    if not cleaned_prefix:
        return PurePosixPath()
    return PurePosixPath(cleaned_prefix)
