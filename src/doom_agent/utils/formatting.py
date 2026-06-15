from __future__ import annotations


def format_path_tail(path: object, max_length: int = 72) -> str:
    value = str(path)
    if len(value) <= max_length:
        return value
    return "..." + value[-(max_length - 3) :]
