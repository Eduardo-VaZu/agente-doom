from __future__ import annotations

import os
from dataclasses import dataclass

from doom_agent.shared.env import load_env_file

STORAGE_BACKEND_ENV_VAR = "AGENTE_DOOM_STORAGE_BACKEND"

S3_BUCKET_ENV_VAR = "AGENTE_DOOM_S3_BUCKET"
S3_REGION_ENV_VAR = "AGENTE_DOOM_S3_REGION"
S3_ACCESS_KEY_ID_ENV_VAR = "AGENTE_DOOM_S3_ACCESS_KEY_ID"
S3_SECRET_ACCESS_KEY_ENV_VAR = "AGENTE_DOOM_S3_SECRET_ACCESS_KEY"
S3_ENDPOINT_URL_ENV_VAR = "AGENTE_DOOM_S3_ENDPOINT_URL"
S3_OBJECT_PREFIX_ENV_VAR = "AGENTE_DOOM_S3_OBJECT_PREFIX"

DEFAULT_STORAGE_BACKEND = "s3"
DEFAULT_OBJECT_PREFIX = "runs"


@dataclass(frozen=True, slots=True)
class S3Settings:
    bucket_name: str
    region: str
    access_key_id: str
    secret_access_key: str
    endpoint_url: str | None
    object_prefix: str


def get_storage_backend() -> str:
    load_env_file()
    configured_backend = os.getenv(STORAGE_BACKEND_ENV_VAR)
    if configured_backend is None or not configured_backend.strip():
        return DEFAULT_STORAGE_BACKEND

    normalized_backend = configured_backend.strip().lower()
    if normalized_backend != "s3":
        raise RuntimeError(
            f"Backend de storage invalido: {configured_backend!r}. Este repo solo soporta 's3'."
        )
    return normalized_backend


def has_explicit_remote_storage_config() -> bool:
    return has_explicit_s3_config()


def has_explicit_s3_config() -> bool:
    load_env_file()
    required_values = [
        os.getenv(S3_BUCKET_ENV_VAR),
        os.getenv(S3_REGION_ENV_VAR),
        os.getenv(S3_ACCESS_KEY_ID_ENV_VAR),
        os.getenv(S3_SECRET_ACCESS_KEY_ENV_VAR),
    ]
    return all(value is not None and bool(value.strip()) for value in required_values)


def get_s3_settings() -> S3Settings:
    load_env_file()
    return S3Settings(
        bucket_name=_require_env(S3_BUCKET_ENV_VAR),
        region=_require_env(S3_REGION_ENV_VAR),
        access_key_id=_require_env(S3_ACCESS_KEY_ID_ENV_VAR),
        secret_access_key=_require_env(S3_SECRET_ACCESS_KEY_ENV_VAR),
        endpoint_url=_optional_env(S3_ENDPOINT_URL_ENV_VAR),
        object_prefix=_resolve_object_prefix(S3_OBJECT_PREFIX_ENV_VAR),
    )


def _resolve_object_prefix(key: str) -> str:
    object_prefix = os.getenv(key, DEFAULT_OBJECT_PREFIX).strip("/")
    if not object_prefix:
        return DEFAULT_OBJECT_PREFIX
    return object_prefix


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or not value.strip():
        raise RuntimeError(f"Variable de entorno requerida ausente: {key}")
    return value.strip()


def _optional_env(key: str) -> str | None:
    value = os.getenv(key)
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized
