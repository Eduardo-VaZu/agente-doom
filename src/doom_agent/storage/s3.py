from __future__ import annotations

from pathlib import Path
from typing import Any

from doom_agent.storage.config import S3Settings, get_s3_settings
from doom_agent.storage.remote import RemoteArtifactLocation


class S3ArtifactStore:
    def __init__(
        self,
        settings: S3Settings | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self._settings = settings or get_s3_settings()
        self._client = client or self._build_client(self._settings)

    def upload_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: str | None = None,
    ) -> RemoteArtifactLocation:
        extra_args: dict[str, Any] = {}
        if content_type is not None:
            extra_args["ContentType"] = content_type

        self._client.upload_file(
            str(local_path),
            self._settings.bucket_name,
            object_key,
            ExtraArgs=extra_args,
        )
        return RemoteArtifactLocation(
            storage_backend="s3",
            bucket_name=self._settings.bucket_name,
            object_key=object_key,
            remote_uri=f"s3://{self._settings.bucket_name}/{object_key}",
            etag=self._head_etag(object_key),
        )

    def download_file(
        self,
        *,
        object_key: str,
        local_path: Path,
    ) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.download_file(
                self._settings.bucket_name,
                object_key,
                str(local_path),
            )
        except Exception as error:
            if self._is_missing_object_error(error):
                raise FileNotFoundError(
                    f"Objeto remoto no encontrado en S3: {self._settings.bucket_name}/{object_key}"
                ) from error
            raise

    @property
    def object_prefix(self) -> str:
        return self._settings.object_prefix

    @property
    def storage_backend(self) -> str:
        return "s3"

    def _head_etag(self, object_key: str) -> str | None:
        response = self._client.head_object(
            Bucket=self._settings.bucket_name,
            Key=object_key,
        )
        etag = response.get("ETag")
        if etag is None:
            return None
        return str(etag).strip('"')

    @staticmethod
    def _is_missing_object_error(error: Exception) -> bool:
        response = getattr(error, "response", None)
        if not isinstance(response, dict):
            return False
        error_payload = response.get("Error")
        if not isinstance(error_payload, dict):
            return False
        error_code = str(error_payload.get("Code", ""))
        return error_code in {"404", "NoSuchKey", "NotFound"}

    @staticmethod
    def _build_client(settings: S3Settings) -> Any:
        try:
            import boto3
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "SDK de AWS no instalado. Ejecuta 'pip install -r requirements.txt'."
            ) from error

        session = boto3.session.Session(
            aws_access_key_id=settings.access_key_id,
            aws_secret_access_key=settings.secret_access_key,
            region_name=settings.region,
        )
        return session.client("s3", endpoint_url=settings.endpoint_url)
