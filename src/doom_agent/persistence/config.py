from __future__ import annotations

import os
from pathlib import Path

from doom_agent.shared.env import load_env_file as _load_env_file

DATABASE_URL_ENV_VAR = "AGENTE_DOOM_DATABASE_URL"
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/agente_doom"


def load_env_file(env_path: Path | None = None) -> None:
    _load_env_file(env_path)


def has_explicit_database_url() -> bool:
    load_env_file()
    configured = os.getenv(DATABASE_URL_ENV_VAR)
    return configured is not None and bool(configured.strip())


def get_database_url(default: str | None = None) -> str:
    load_env_file()
    resolved = os.getenv(DATABASE_URL_ENV_VAR, default or DEFAULT_DATABASE_URL).strip()
    if not resolved:
        raise RuntimeError(
            f"No database URL configured. Define '{DATABASE_URL_ENV_VAR}' o ajusta alembic.ini."
        )
    return resolved
