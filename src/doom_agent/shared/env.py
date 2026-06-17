from __future__ import annotations

import os
from pathlib import Path

ENV_FILE_NAME = ".env"


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    cleaned_key = key.strip()
    cleaned_value = value.strip()
    if not cleaned_key:
        return None

    if len(cleaned_value) >= 2 and cleaned_value[0] == cleaned_value[-1] and cleaned_value[0] in {
        '"',
        "'",
    }:
        cleaned_value = cleaned_value[1:-1]
    return cleaned_key, cleaned_value


def load_env_file(env_path: Path | None = None) -> None:
    resolved_env_path = env_path or (project_root() / ENV_FILE_NAME)
    if not resolved_env_path.exists():
        return

    for raw_line in resolved_env_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)
