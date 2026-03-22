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


def reverse_replacements(operations: list[dict[str, str | int]]) -> list[tuple[str, str]]:
    reverse: dict[str, str] = {}
    for operation in operations:
        source = str(operation["source"])
        target = str(operation["target"])
        existing = reverse.get(target)
        if existing is not None and existing != source:
            raise ValueError(
                f"Ambiguous reverse replacement for target '{target}': '{existing}' and '{source}'"
            )
        reverse[target] = source
    return _sorted_replacements(reverse.items())


def _sorted_replacements(
    replacements: dict[str, str] | Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    items = replacements.items() if isinstance(replacements, dict) else list(replacements)
    return sorted(items, key=lambda item: (-len(item[0]), item[0].lower(), item[1]))
