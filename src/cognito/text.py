from __future__ import annotations

import re
from collections.abc import Iterable


def replace_case_insensitive(
    content: str,
    replacements: dict[str, str] | Iterable[tuple[str, str]],
) -> tuple[str, list[dict[str, str | int]]]:
    updated = content
    operations: list[dict[str, str | int]] = []
    for source, target in _sorted_replacements(replacements):
        pattern = re.compile(re.escape(source), re.IGNORECASE)
        updated, count = pattern.subn(target, updated)
        if count:
            operations.append({"source": source, "target": target, "count": count})
    return updated, operations


def _sorted_replacements(
    replacements: dict[str, str] | Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    items = replacements.items() if isinstance(replacements, dict) else list(replacements)
    return sorted(items, key=lambda item: (-len(item[0]), item[0].lower(), item[1]))
