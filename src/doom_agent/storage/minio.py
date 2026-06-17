from __future__ import annotations

from pathlib import Path
from typing import Any

from doom_agent.storage.config import MinioSettings, get_minio_settings
from doom_agent.storage.remote import RemoteArtifactLocation, build_remote_uri


class MinioArtifactStore:
    def __init__(
        self,
        settings: MinioSettings | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self._settings = settings or get_minio_settings()
        self._client = client or self._build_client(self._settings)

    def upload_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: str | None = None,
    ) -> RemoteArtifactLocation:
        self._ensure_bucket_exists()
        result = self._client.fput_object(
            self._settings.bucket_name,
            object_key,
            str(local_path),
            content_type=content_type,
        )
        etag = getattr(result, "etag", None)
        return RemoteArtifactLocation(
            storage_backend="minio",
            bucket_name=self._settings.bucket_name,
            object_key=object_key,
            remote_uri=build_remote_uri(self._settings.bucket_name, object_key),
            etag=None if etag is None else str(etag),
        )

    @property
    def object_prefix(self) -> str:
        return self._settings.object_prefix

    def _ensure_bucket_exists(self) -> None:
        if self._client.bucket_exists(self._settings.bucket_name):
            return
        self._client.make_bucket(self._settings.bucket_name)

    @staticmethod
    def _build_client(settings: MinioSettings) -> Any:
        try:
            from minio import Minio
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "SDK de MinIO no instalado. Ejecuta 'pip install -r requirements.txt'."
            ) from error

        return Minio(
            settings.endpoint,
            access_key=settings.access_key,
            secret_key=settings.secret_key,
            secure=settings.secure,
            region=settings.region,
        )
