from __future__ import annotations

from collections.abc import Iterable


def _stringify(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def build_kv_lines(items: Iterable[tuple[str, object]]) -> list[str]:
    entries = [(label, _stringify(value)) for label, value in items]
    if not entries:
        return []

    key_width = max(len(label) for label, _ in entries)
    return [f"{label.ljust(key_width)} : {value}" for label, value in entries]


def print_block(title: str, lines: Iterable[str]) -> None:
    content = list(lines)
    width = max([len(title), *(len(line) for line in content)], default=len(title))
    border = "+" + ("-" * (width + 2)) + "+"
    print(border)
    print(f"| {title.ljust(width)} |")
    print(border)
    for line in content:
        print(f"| {line.ljust(width)} |")
    print(border)


def print_kv_block(title: str, items: Iterable[tuple[str, object]]) -> None:
    print_block(title, build_kv_lines(items))
